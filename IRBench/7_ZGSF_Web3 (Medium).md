**Source**: [https://pan.quark.cn/s/4b6dffd0c51a](https://pan.quark.cn/s/4b6dffd0c51a) (ZGSF_Web3) 
**Type**: Web Compromise & Database Forensics
#### Keywords
- Web Log Analysis
- Hidden Account
- Scheduled Task Persistence
- Database Forensics
#### Scena
A web server has been compromised involving multiple attacker IPs. The attacker established persistence via scheduled tasks, created a hidden user, and tampered with the database. You need to trace the attack, identify the flags in various locations (files, tasks, database), and restore the system.
#### Sub-task LIst
|     | Task                       | Types of Sub-task                                     |
| --- | -------------------------- | ----------------------------------------------------- |
| 1   | Attacker's first IP        | Application Log Analysis                              |
| 2   | Attacker's second IP       | Application Log Analysis                              |
| 3   | Hide user name             | Directory Inspection/Permission Review and Management |
| 4   | Attacker's first flag      | Directory Inspection/File Analysis                    |
| 5   | Attacker's second flag     | Scheduled Task Analysis                               |
| 6   | Attacker's third flag      | File Analysis/Database Analysis<br>                   |
| 7   | Risky IP Management        | Risky IP Management                                   |
| 8   | Delete unauthorized user   | Permission Review and Management                      |
| 9   | Handle webshell            | Malicious File Handling                               |
| 10  | Handle malicious scheduled | Anomaly Behavior Response                             |
| 11  | Recover the database       | Data Recovery                                         |
