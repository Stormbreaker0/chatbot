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

tmp_dir = TemporaryDirectory()
# Get the token from the .env file
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOOTBALL_TEAMS_API = os.getenv("FOOTBALL_TEAMS_API")
FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
FOOTBALL_SCORES_API = os.getenv("FOOTBALL_SCORES_API")
TIMER = 180

# Set up logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dizionario per tenere traccia dei lavori (monitoraggi) in corso
active_jobs = {}
team_results = []


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


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

        await update.message.reply_document(document=output, filename="teams_list.txt")


async def get_all_matchs():
    async with aiohttp.ClientSession() as client:
        headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection" : "keep-alive",
            "Access-Control-Allow-Headers":"Keep-Alive,User-Agent,X-Requested-With,Cache-Control,Content-Type,Authorization,user_data,pragma,channel,tokenKeep-Alive,User-Agent,X-Requested-With,Cache-Control,Content-Type,Authorization,user_data,pragma,channel,token",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"
        }
        today = datetime.datetime.now().strftime("%d-%m-%Y")
        request_url = os.path.join(FOOTBALL_SCORES_API, today)
        response = await client.get(request_url, headers=headers)
        if response.status == 200:
            results = await response.json()[0]
            return results
        logger.info(f"Errore nell'ottenere i dati: {response.status}")
        return []

def format_results_table(results, desired_outcome):
    table = "| Squadra Casa | Squadra Trasferta | Risultato | Esito |\n"
    table += "|--------------|------------------|-----------|-------|\n"

    for match in results:
        home_team = match['home_team']
        away_team = match['away_team']
        score_home = match['score_home']
        score_away = match['score_away']
        
        if desired_outcome == 'Pareggio' and score_home == score_away:
            outcome = "Pareggio"
        elif desired_outcome == 'Vittoria' and score_home > score_away:
            outcome = f"{home_team} ha vinto"
        elif desired_outcome == 'Vittoria' and score_away > score_home:
            outcome = f"{away_team} ha vinto"
        else:
            continue

        table += f"| {home_team}      | {away_team}         | {score_home}-{score_away}   | {outcome} |\n"

    return table

async def check_results(context: CallbackContext):
    data = context.job.data
    team, numero, desired_outcome = data.split(':')
    table = ""
    count = 0

    all_matchs = await get_all_matchs()
    for data_dict in all_matchs:
        home_team, away_team = data_dict['descrizioneAvventimento'].split(' - ')
        score = data_dict['risultato'].split('-')
        score_home = int(score[0])
        score_away = int(score[1])

        if home_team == team:
            # null
            if desired_outcome.lower() == 'pareggio' and score_home == score_away and home_team == team:
                outcome = "Pareggio"
            # win
            elif desired_outcome.lower() == 'Vittoria' and score_home > score_away:
                outcome = "Vittoria"
            # loss
            else:
                continue
        if away_team == team:
            # null
            if desired_outcome.lower() == 'pareggio' and score_home == score_away:
                outcome = "Pareggio"
            # win
            elif desired_outcome.lower() == 'Vittoria' and score_home > score_away:
                outcome = "Vittoria"
            elif desired_outcome.lower() == 'Vittoria' and score_away > score_home:
                outcome = f"Vittoria"

            # loss
        # results render
        # table = format_results_table(results, desired_outcome)

    if table:
        await context.bot.send_message(chat_id=context.job.context['chat_id'], text=f"**Risultati con esito desiderato: {desired_outcome}**\n\n{table}")

async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0 or len(context.args) > 3:
        await update.message.reply_text("Utilizzo corretto: /get_results <Squadra> <Numero> <Esito desiderato>")
        return

    try:
        team, numero = context.args[:-1]
        desired_outcome = context.args[-1]
    except Exception as e:
        logger.exception(e, "Setting default arguments")
        numero = 3
        desired_outcome = "vittoria"

    chat_id = update.message.chat_id
    data = f"{team}:{numero}:{desired_outcome}"

    job = context.job_queue.run_repeating(check_results, interval=TIMER, data=data, chat_id=chat_id, name=str(f"job-{chat_id}"))

    active_jobs[chat_id] = job
    logger.info(active_jobs)
    logger.info(f"Inizio monitoraggio risultati per le squadre {', '.join(team)} con esito desiderato: {desired_outcome}")

    await update.message.reply_text(f"Inizio monitoraggio risultati per le squadre {', '.join(team)} con esito desiderato: {desired_outcome}")

async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    job_id = f"job-{chat_id}"
    if job_id in active_jobs:
        # Ferma il lavoro
        job = active_jobs.pop(chat_id)
        job.schedule_removal()
        await update.message.reply_text("Monitoraggio fermato.")
    else:
        await update.message.reply_text("Non c'è alcun monitoraggio attivo.")

async def stop_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for chat_id in list(active_jobs.keys()):
        job_id = f"job-{chat_id}"
        job = active_jobs.pop(job_id)
        job.schedule_removal()
    await update.message.reply_text("Tutti i monitoraggi sono stati fermati.")

def main():
    """Start the bot."""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler('teams', get_codes_teams))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler('set_team', start_monitoring))
    app.add_handler(CommandHandler("stop", stop_monitoring))
    app.add_handler(CommandHandler("stop_all", stop_all))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
