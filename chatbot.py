import logging
import os
import datetime
import json
import aiohttp
import pandas as pd
from tempfile import TemporaryDirectory
from dotenv import load_dotenv
from telegram import Update
from io import StringIO
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext

# Load environment variables from the .env file
load_dotenv()


tmp_dir= TemporaryDirectory()
tmp_dir.cleanup()
# Get the token from the .env file
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

FOOTBALL_TEAMS_API = os.getenv("FOOTBALL_TEAMS_API")

FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")


FOOTBALL_SCORES_API = os.getenv("FOOTBALL_SCORES_API")

# Set up logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dizionario per tenere traccia dei lavori (monitoraggi) in corso
active_jobs = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def set_timer_notification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def stop_notification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def get_codes_teams(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with aiohttp.ClientSession() as client:
        res = await client.get(FOOTBALL_TEAMS_API, headers={"X-Auth-Token": FOOTBALL_DATA_TOKEN})

        logger.info(res.status)
        data = await res.json()
        # logger.info(data)
        teams_list = []
        # await update.message.reply_text(str(res.status))
          # Iterate over the teams and collect relevant data
        for items in data['teams']:
            team_name = items['name']
            team_code = items['tla']
            teams_list.append([team_name, team_code])

        # # Create a pandas DataFrame from the list
        # teams_df = pd.DataFrame(teams_list, columns=['Nome squadra', 'Codice squadra'])

        # # Log the DataFrame (optional)
        # logger.info(teams_df)
        
        # await update.message.reply_text(teams_df.to_string(index=True))

        # Create a pandas DataFrame from the list
        teams_df = pd.DataFrame(teams_list, columns=['Nome squadra', 'Codice squadra'])

        # Log the DataFrame (optional)
        logger.info(teams_df)

        # Save the DataFrame to a StringIO object as a text file
        output = StringIO()
        teams_df.to_csv(output, index=True, sep='\t')
        output.seek(0)

        # Send the file to Telegram
        await update.message.reply_document(document=output, filename="teams_list.txt")


async def get_match_result(team):
    async with aiohttp.ClientSession() as client:
        headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection" : "keep-alive",
            "Access-Control-Allow-Headers":"Keep-Alive,User-Agent,X-Requested-With,Cache-Control,Content-Type,Authorization,user_data,pragma,channel,token",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"
        }
        today = datetime.datetime.now().strftime("%d-%m-%Y")
        request_url = os.path.join(FOOTBALL_SCORES_API, today)
        response = await client.get(request_url, headers=headers)
        if response.status == 200:
            data = await response.json()
            results = []
            for data_dict in data:
                teams = data_dict['descrizioneAvventimento'].split(' - ')
                if team in teams:
                    print(team)


            return results

        return []

# Funzione che crea una tabella formattata
def format_results_table(results, desired_outcome):
    table = "| Squadra Casa | Squadra Trasferta | Risultato | Esito |\n"
    table += "|--------------|------------------|-----------|-------|\n"
    
    for match in results:
        home_team = match['home_team']
        away_team = match['away_team']
        score_home = match['score_home']
        score_away = match['score_away']
        
        # Determina l'esito della partita
        if desired_outcome == 'Pareggio' and score_home == score_away:
            outcome = "Pareggio"
        elif desired_outcome == 'Vittoria' and score_home > score_away:
            outcome = f"{home_team} ha vinto"
        elif desired_outcome == 'Vittoria' and score_away > score_home:
            outcome = f"{away_team} ha vinto"
        else:
            continue  # Se non corrisponde all'esito, salta la partita

        # Aggiungi la partita alla tabella
        table += f"| {home_team}      | {away_team}         | {score_home}-{score_away}   | {outcome} |\n"
    
    return table

# Funzione che verifica se l'esito della partita corrisponde
async def check_results(data, context: CallbackContext):
    # Verifica per ogni squadra
    teams, desired_outcome = data.split(':')
    print(teams)
    table = ""
    for team in teams:
        results = await get_match_result(team)
        
        for match in results:
            home_team = match['home_team']
            away_team = match['away_team']
            score_home = match['score_home']
            score_away = match['score_away']

            # Determina l'esito
            if desired_outcome == 'Pareggio' and score_home == score_away:
                outcome = "Pareggio"
            elif desired_outcome == 'Vittoria' and score_home > score_away and home_team == team:
                outcome = f"{home_team} ha vinto"
            elif desired_outcome == 'Vittoria' and score_away > score_home and away_team == team:
                outcome = f"{away_team} ha vinto"
            else:
                continue  # Se non corrisponde all'esito, salta la partita
            
            # Crea la tabella per i risultati
            table = format_results_table(results, desired_outcome)
    
    # Se ci sono risultati, invia la tabella
    if table:
        context.bot.send_message(chat_id=context.job.context['chat_id'], text=f"**Risultati con esito desiderato: {desired_outcome}**\n\n{table}")

    # Riavvia il controllo ogni 3 minuti
    context.job_queue.run_once(check_results, 10, context=context.job.context)

async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Funzione per avviare il monitoraggio
    if len(context.args) < 0:
        await update.message.reply_text("Utilizzo corretto: /get_results <Squadra1> <Timer> ... <Esito desiderato>")
        return

    teams = context.args[:-1]  # tutte le squadre tranne l'ultimo argomento (esito)
    desired_outcome = context.args[-1]  # l'ultimo argomento è l'esito desiderato
    chat_id = update.message.chat_id
    data = f"{teams}:{desired_outcome}"

    # Crea un lavoro per il monitoraggio
    job = context.job_queue.run_once(check_results, 10, data=data, name=str(chat_id), chat_id=chat_id)

    # Salva il lavoro nel dizionario active_jobs
    active_jobs[chat_id] = job
    logger.info(active_jobs)
    logger.info(f"Inizio monitoraggio risultati per le squadre {', '.join(teams)} con esito desiderato: {desired_outcome}")

    await update.message.reply_text(f"Inizio monitoraggio risultati per le squadre {', '.join(teams)} con esito desiderato: {desired_outcome}")


# Funzione per fermare il monitoraggio
async def stop_monitoring(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    if chat_id in active_jobs:
        # Fermiamo il lavoro associato a questo chat_id
        active_jobs[chat_id].schedule_removal()
        del active_jobs[chat_id]
        update.message.reply_text("Monitoraggio fermato.")
    else:
        update.message.reply_text("Non c'è alcun monitoraggio attivo.")


def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # on different commands - answer in Telegram
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler('teams', get_codes_teams))

    app.add_handler(CommandHandler("help", help_command))

    #on non command i.e message - echo the message on Telegram
    app.add_handler(CommandHandler('get_results', start_monitoring))

    # app.add_handler(CommandHandler("set", set_timer_notification))

    app.add_handler(CommandHandler("stop", stop_monitoring))

    # Run the bot until the user presses Ctrl-C
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
