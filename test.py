async def check_results(context: CallbackContext):
    data = [
        {'home_team': 'JUV', 'away_team': 'INT', 'esito': 'Vittoria', 'data': '03-01-2025:13:55', 'partita': 'JUV - INT', 'risultato': '0-1', 'partita_id': '2500300031_416'},
        {'home_team': 'INT', 'away_team': 'NAP', 'esito': 'Vittoria', 'data': '03-01-2025:13:18', 'partita': 'INT - NAP', 'risultato': '1-0', 'partita_id': '2500300031_385'},
        {'home_team': 'SAM', 'away_team': 'INT', 'esito': 'Vittoria', 'data': '03-01-2025:13:16', 'partita': 'SAM - INT', 'risultato': '0-1', 'partita_id': '2500300031_383'},
        {'home_team': 'INT', 'away_team': 'NAP', 'esito': 'Vittoria', 'data': '03-01-2025:12:42', 'partita': 'INT - NAP', 'risultato': '1-0', 'partita_id': '2500300031_358'},
        {'home_team': 'INT', 'away_team': 'ROM', 'esito': 'Vittoria', 'data': '03-01-2025:12:25', 'partita': 'INT - ROM', 'risultato': '2-1', 'partita_id': '2500300031_347'},
        {'home_team': 'INT', 'away_team': 'NAP', 'esito': 'Vittoria', 'data': '03-01-2025:12:06', 'partita': 'INT - NAP', 'risultato': '3-0', 'partita_id': '2500300031_334'},
        {'home_team': 'SAM', 'away_team': 'INT', 'esito': 'Vittoria', 'data': '03-01-2025:11:52', 'partita': 'SAM - INT', 'risultato': '2-3', 'partita_id': '2500300031_324'},
        {'home_team': 'INT', 'away_team': 'UDI', 'esito': 'Vittoria', 'data': '03-01-2025:11:07', 'partita': 'INT - UDI', 'risultato': '2-0', 'partita_id': '2500300031_295'},
        {'home_team': 'MIL', 'away_team': 'INT', 'esito': 'Vittoria', 'data': '03-01-2025:09:37', 'partita': 'MIL - INT', 'risultato': '0-2', 'partita_id': '2500300031_234'},
        {'home_team': 'GEN', 'away_team': 'INT', 'esito': 'Vittoria', 'data': '03-01-2025:08:19', 'partita': 'GEN - INT', 'risultato': '0-2', 'partita_id': '2500300031_182'},
        {'home_team': 'INT', 'away_team': 'FIO', 'esito': 'Vittoria', 'data': '03-01-2025:07:49', 'partita': 'INT - FIO', 'risultato': '4-0', 'partita_id': '2500300031_162'},
        {'home_team': 'INT', 'away_team': 'ROM', 'esito': 'Vittoria', 'data': '03-01-2025:02:55', 'partita': 'INT - ROM', 'risultato': '3-2', 'partita_id': '2500300031_136'},
        {'home_team': 'SAM', 'away_team': 'INT', 'esito': 'Vittoria', 'data': '03-01-2025:02:43', 'partita': 'SAM - INT', 'risultato': '1-4', 'partita_id': '2500300031_128'},
        {'home_team': 'ROM', 'away_team': 'INT', 'esito': 'Vittoria', 'data': '03-01-2025:01:49', 'partita': 'ROM - INT', 'risultato': '2-3', 'partita_id': '2500300031_92'},
        {'home_team': 'INT', 'away_team': 'MIL', 'esito': 'Vittoria', 'data': '03-01-2025:01:31', 'partita': 'INT - MIL', 'risultato': '1-0', 'partita_id': '2500300031_77'}
    ]

    # Manually create HTML table
    table = "<table border='1' cellspacing='0' cellpadding='5'>"
    table += "<tr><th>Home Team</th><th>Away Team</th><th>Esito</th><th>Data</th><th>Risultato</th></tr>"
    for match in data:
        table += f"<tr><td>{match['home_team']}</td><td>{match['away_team']}</td><td>{match['esito']}</td><td>{match['data']}</td><td>{match['risultato']}</td></tr>"
    table += "</table>"

    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=table,
        parse_mode="HTML"
    )
