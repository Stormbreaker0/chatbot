# chatbot
Questo progetto è un Telegram BOT per attività/lavori pianificati per ottenere una serie di risultati desiderati di una singola squadra per una partita di calcio virtuale


# Documentation
- Lista dei comandi:
    * /start per avviare il bot
    * /stop per fermare tutti i jobs in corso
    * /imposta <CodiceSquadra> <Numero> <Esito> per impostare i risultati per la squadra di interesso. il bot controlla se ci risultati disponibili per un numero di esito consecutivi inseriti. Esempio: "ROM 2 Perdita" manda la notifica ogni volta che la Roma perde 2 volte consecutive
    */timer <minuti> imposta l'intervallo di controllo dei risultati dal bot, se disponibile verranno inviati. Di default sono 3 minuti
    */aiuto fornisce informazioni sul bot 