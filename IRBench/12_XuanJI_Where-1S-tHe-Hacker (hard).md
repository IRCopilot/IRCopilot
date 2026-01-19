**Source**: [https://xj.edisec.net/challenges/63](https://xj.edisec.net/challenges/63) (Where-1S-tHe-Hacker) 
**Type**: Windows Advanced Persistence & Defacement Response
#### Keywords
- Windows Log Analysis (Event ID 4720, 4624)
- Pass-The-Hash (PTH) Analysis
- Hidden Account ($)
- Web Defacement Recovery
#### Scenario
A Windows server's website has been defaced. The attacker not only modified the web pages but also created hidden system accounts, utilized Pass-The-Hash (PTH) for lateral movement, and accessed sensitive files. You need to reconstruct the entire attack timeline via logs and artifacts, and perform a full system recovery.
#### Sub-task LIst
|     | Task                                                                                                     | Types of Sub-task                              |
| --- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| 1   | What is the hacker ID                                                                                    | Directory Inspection/File Analysis             |
| 2   | When did the hacker modify the homepage of the website?                                                  | File Integrity Check                           |
| 3   | The name of the hacker's first webshell file                                                             | Directory Inspection/File Analysis             |
| 4   | The name of the hacker's second webshell file                                                            | Directory Inspection/File Analysis             |
| 5   | The connection password of the hacker's second webshell                                                  | Directory Inspection/File Analysis             |
| 6   | The hacker's newly created hidden account                                                                | Account Security Review                        |
| 7   | Find the time when the hacker's hidden account was created                                               | Permission Review/System Log Analysis          |
| 8   | The time when the hacker added the hidden account to the local                                           | Permission Review/System Log Analysis          |
| 9   | The time when the hacker read the reserved key from the file                                             | System Log Analysis                            |
| 10  | The time when the hacker logged in through the hidden account through the (PTH) hash pass-through attack | System Log Analysis                            |
| 11  | Recover the homepage                                                                                     | Service Recovery                               |
| 12  | Handle the first webshell                                                                                | Malicious File Handling                        |
| 13  | Handle the second webshell                                                                               | Malicious File Handling                        |
| 14  | Delete unauthorized user                                                                                 | Permission Review and Management               |
| 15  | Check the hash                                                                                           | File Integrity Check/Anomaly Behavior Response |
