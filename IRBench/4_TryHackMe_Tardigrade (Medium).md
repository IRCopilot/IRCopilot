**Source**: [https://tryhackme.com/r/room/tardigrade](https://tryhackme.com/r/room/tardigrade) 
**Type**: Linux Post-Compromise Investigation
#### Keywords
- Linux Forensics
- Persistence Analysis (Cron, .bashrc)
- Privilege Escalation
- Account Security
#### Scenario
A Linux server has been compromised. The goal is to identify the persistence mechanisms (cron jobs, bashrc modifications), identify the attacker's traces, and restore the system.
#### Sub-task LIst
|     | Task                                                                                                                                                                                                   | Types of Sub-task                                                   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| 1   | What is the server’s OS version?                                                                                                                                                                       | System Information Gathering                                        |
| 2   | What’s the most interesting file you found in giorgio’s home directory?                                                                                                                                | Directory Inspection                                                |
| 3   | Can you check if you can find something interesting in giorgio’s .bashrc?                                                                                                                              | Startup Item Analysis                                               |
| 4   | Did you find anything interesting about scheduled tasks?                                                                                                                                               | Scheduled Task Analysis                                             |
| 5   | A few moments after logging on to the root account, you find an error message in your terminal. What does it say?                                                                                      | Permission Review and Management/Startup Item Analysis              |
| 6   | After moving forward with the error message, a suspicious command appears in the terminal as part of the error message. What command was displayed?                                                    | Permission Review and Management/Startup Item Analysis              |
| 7   | Can you find out how the suspicious command has been implemented?                                                                                                                                      | Startup Item Analysis                                               |
| 8   | What is the last persistence mechanism?                                                                                                                                                                | Account Security Review/Permission Review and Management            |
| 9   | Finally, as you’ve already found the final persistence mechanism, there’s value in going all the way through to the end. The adversary left a golden nugget of “advise” somewhere. What is the nugget? | Directory Inspection/File Analysis/Permission Review and Management |
| 10  | Handle .bad_bash                                                                                                                                                                                       | Malicious File Handling                                             |
| 11  | Handle .bashrc                                                                                                                                                                                         | System Recovery                                                     |
| 12  | Handle malicious scheduled                                                                                                                                                                             | Anomaly Behavior Response                                           |
| 13  | Manage malicious IP                                                                                                                                                                                    | Risky IP Management                                                 |
| 14  | Malicious Process Handling                                                                                                                                                                             | Malicious Process Handling                                          |
| 15  | Delete unauthorized user                                                                                                                                                                               | Account Security Review/Permission Review and Management            |
