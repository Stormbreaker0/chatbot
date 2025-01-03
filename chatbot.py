import os
import logging
import datetime
import aiohttp
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from io import StringIO
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext

# Load environment variables from the .env file
load_dotenv()

# Get the token from the .env file
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOOTBALL_TEAMS_API = os.getenv("FOOTBALL_TEAMS_API")
FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
FOOTBALL_SCORES_API = os.getenv("FOOTBALL_SCORES_API")
TIMER = 300

TODAY = datetime.datetime.now().strftime("%d-%m-%Y")

OLD_TABLE = ""
# Set up logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dizionario per tenere traccia dei lavori (monitoraggi) in corso
active_jobs = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Ciao {update.effective_user.first_name}')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Aiuto!")


async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set global timer"""

    try:
        # args[0] should contain the time for the timer in minutes
        minutes = float(context.args[0])
        seconds = minutes * 60

        if seconds < 0:
            await update.effective_message.reply_text("Sorry, we cannot go back to the future!")
            return

        await stop_all(update=update, context=context)
        global TIMER
        TIMER = seconds
        text = "Timer impostato con successo!\n Reimposta la squadra!"

        await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Usage: /timer <minutes>")


async def get_codes_teams(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with aiohttp.ClientSession() as client:
        res = await client.get(FOOTBALL_TEAMS_API, headers={"X-Auth-Token": FOOTBALL_DATA_TOKEN})
        logger.info(res.status)
        data = await res.json()
        teams_list = []

        for items in data['teams']:
            team_name = items['name']
            team_code = items['tla']
            teams_list.append([team_name, team_code])

        teams_df = pd.DataFrame(teams_list, columns=['Nome squadra', 'Codice squadra'])
        logger.info(teams_df)

        output = StringIO()
        teams_df.to_csv(output, index=True, sep='\t')
        output.seek(0)

        await update.message.reply_document(document=output, filename="squadre.txt")


async def get_all_matchs():
    async with aiohttp.ClientSession() as client:
        headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection" : "keep-alive",
            "Access-Control-Allow-Headers":"Keep-Alive,User-Agent,X-Requested-With,Cache-Control,Content-Type,Authorization,user_data,pragma,channel,tokenKeep-Alive,User-Agent,X-Requested-With,Cache-Control,Content-Type,Authorization,user_data,pragma,channel,token",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"
        }
        
        request_url = os.path.join(FOOTBALL_SCORES_API, TODAY)
        response = await client.get(request_url, headers=headers)
        if response.status == 200:
            results = await response.json()
            return results
        logger.info(f"Errore nell'ottenere i dati: {response.status}")
        return []


async def verifica_esito_consecutive(lista_dizionari, n, esito):
    count = 0
    ultime_partite = lista_dizionari[:n]  # Prendi le ultime n partite
    for partita in ultime_partite:
        if partita['esito'].lower() == esito:
            count += 1
        else:
            return False  # Se trovi una partita che non è una vittoria, restituisci False
    return count == n  # Restituisce True solo se tutte le n partite sono vittorie


async def format_table_as_markdown(data):
    table = "```\n"
    headers = "home_team | away_team | risultato | data"
    table += headers + "\n"
    table += "-" * len(headers) + "\n"
    for item in data:
        row = f"{item['home_team']} | {item['away_team']} | {item['risultato']} | {item['data']}"
        table += row + "\n"
    table += "```"
    return table


async def check_results(context: CallbackContext):
    data = context.job.data
    team, numero, desired_outcome = data.split(':')
    numero = int(numero)
    logger.info(f"{team} {numero} {desired_outcome}")
    output = []
    outcome = ""
    desired_outcome = desired_outcome.lower()

    all_matchs = await get_all_matchs()
    for data_dict in all_matchs:
        outcome = ""
        home_team, away_team = data_dict['descrizioneAvventimento'].split(' - ')
        single_data = {
            'home_team': home_team,
            'away_team': away_team
                       
        }
        score_home, score_away = map(int, data_dict['risultato'].split('-'))

        if (home_team == team and desired_outcome == 'pareggio' and score_home == score_away) or \
           (away_team == team and desired_outcome == 'pareggio' and score_home == score_away):
            outcome = "Pareggio"
            single_data['esito'] = outcome
            single_data['data'] = f"{TODAY}H{data_dict['dataOra']}"
            single_data['partita'] = data_dict['descrizioneAvventimento']
            single_data['risultato'] = data_dict['risultato']
            single_data['partita_id'] = f"{data_dict['codicePalinsesto']}_{data_dict['codiceAvvenimento']}"

        elif (home_team == team and desired_outcome == 'vittoria' and score_home > score_away) or \
             (away_team == team and desired_outcome == 'vittoria' and score_home < score_away):
            outcome = "Vittoria"
            single_data['esito'] = outcome
            single_data['data'] = f"{TODAY}H{data_dict['dataOra']}"
            single_data['partita'] = data_dict['descrizioneAvventimento']
            single_data['risultato'] = data_dict['risultato']
            single_data['partita_id'] = f"{data_dict['codicePalinsesto']}_{data_dict['codiceAvvenimento']}"
        elif (home_team == team and desired_outcome == 'perdita' and score_home < score_away) or \
             (away_team == team and desired_outcome == 'perdita' and score_home > score_away):
            outcome = "Perdita"
            single_data['esito'] = outcome
            single_data['data'] = f"{TODAY}H{data_dict['dataOra']}"
            single_data['partita'] = data_dict['descrizioneAvventimento']
            single_data['risultato'] = data_dict['risultato']
            single_data['partita_id'] = f"{data_dict['codicePalinsesto']}_{data_dict['codiceAvvenimento']}"

        if outcome:
            output.append(single_data)

    if output:
        logger.info(output)
        if await verifica_esito_consecutive(output, numero, desired_outcome):
            ultime_partite = output[:numero]
            new_table = await format_table_as_markdown(ultime_partite)
            global OLD_TABLE
            if new_table != OLD_TABLE:
                await context.bot.send_message(chat_id=context.job.chat_id, text=new_table, parse_mode="Markdown")
                OLD_TABLE = new_table
            else:
                logger.info("same output as the last one")
        else:
            logger.info("Any output available")
    else:
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=f"Risultati not found now!"
        )


async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0 or len(context.args) > 3:
        await update.message.reply_text("Utilizzo corretto: /imposta <Squadra> <Numero> <Esito desiderato>")
        return

    try:
        team, numero = context.args[:-1]
        desired_outcome = context.args[-1]
    except Exception as e:
        logger.info(e, "Setting default arguments")
        numero = 3
        desired_outcome = "vittoria"

    chat_id = update.message.chat_id
    data = f"{team}:{numero}:{desired_outcome}"

    job = context.job_queue.run_repeating(check_results, first=1, interval=TIMER, data=data, chat_id=chat_id, name=str(chat_id))

    active_jobs[chat_id] = job
    logger.info(active_jobs)
    logger.info(f"Inizio monitoraggio risultati per la squadra {str(team)}\nEsito desiderato: {desired_outcome}\nNumero di esito consecutive: {numero}")

    await update.message.reply_text(f"Inizio monitoraggio risultati per la squadra {str(team)}\nEsito desiderato: {desired_outcome}\nNumero di esito consecutive: {numero}")


async def stop_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for chat_id in list(active_jobs.keys()):
        job = active_jobs.pop(chat_id)
        job.schedule_removal()
    logger.info("Tutti i monitoraggi sono stati fermati.")
    await update.message.reply_text("L'invio delle notifiche è stato fermato")
   

def main():
    """Start the bot."""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler('squadre', get_codes_teams))
    app.add_handler(CommandHandler("aiuto", help_command))
    app.add_handler(CommandHandler('imposta', start_monitoring))
    app.add_handler(CommandHandler("stop", stop_all))
    app.add_handler(CommandHandler("timer", set_timer))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
