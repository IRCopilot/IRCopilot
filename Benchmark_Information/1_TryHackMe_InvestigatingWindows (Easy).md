https://tryhackme.com/r/room/investigatingwindows
#### Sub-task LIst
|     | Task                                                                                            | Types of Sub-task                                            |
| --- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 1   | Whats the version and year of the windows machine?                                              | System Information Gathering                                 |
| 2   | Which user logged in last?                                                                      | Account Security Review                                      |
| 3   | When did John log onto the system last?                                                         | Account Security Review                                      |
| 4   | What IP does the system connect to when it first starts?                                        | Startup Item Analysis                                        |
| 5   | What two accounts had administrative privileges (other than the Administrator user)?            | Permission Review                                            |
| 6   | Whats the name of the scheduled task that is malicous.                                          | Scheduled Task Analysis                                      |
| 7   | What file was the task trying to run daily?                                                     | Scheduled Task Analysis                                      |
| 8   | What port did this file listen locally for?                                                     | Scheduled Task Analysis/File Analysis                        |
| 9   | When did Jenny last logon?                                                                      | Account Security Review                                      |
| 10  | At what date did the compromise take place?                                                     | System Log Analysis                                          |
| 11  | During the compromise, at what time did Windows first assign special privileges to a new logon? | Permission Review/System Log Analysis                        |
| 12  | What tool was used to get Windows passwords?                                                    | Directory Inspection/File Analysis/Anomaly Behavior Response |
| 13  | What was the attackers external control and command servers IP?                                 | File Analysis/Network Traffic Analysis                       |
| 14  | What was the extension name of the shell uploaded via the servers website?                      | File Analysis                                                |
| 15  | What was the last port the attacker opened?                                                     | Other Response/Anomaly Behavior Response                     |
| 16  | Check for DNS poisoning, what site was targeted?                                                | File Analysis/Network Traffic Analysis                       |
| 17  | Permission Review and Management                                                                | Permission Review and Management                             |
| 18  | Remove malicious scheduled tasks                                                                | Anomaly Behavior Response                                    |
| 19  | Clean up files that are run daily by malicious scheduled tasks                                  | Malicious File Handling                                      |
| 20  | Remove malicious files mimikatz                                                                 | Malicious File Handling                                      |
| 21  | Clear malicious file shell                                                                      | Malicious File Handling                                      |
| 22  | Clear malicious DNS and block malicious IP                                                      | Risky IP Management                                          |
