**Source**: [https://pan.quark.cn/s/4b6dffd0c51a](https://pan.quark.cn/s/4b6dffd0c51a) (ZGSF_WindowsMiner) 
**Type**: Windows Cryptojacking Response
#### Keywords
- Windows Log Analysis (RDP Brute-force)
- Cryptojacking (Mining)
- Process Analysis
- Malware Hash Identification
#### Scenario
A Windows server is experiencing abnormal performance issues. An attacker has bruteforced the system and deployed a cryptocurrency miner along with a persistence backdoor. You need to analyze the security logs, identify the resource-hogging processes, extract the mining configuration (wallet/pool), and clean the system.
#### Sub-task LIst
|     | Task                                        | Types of Sub-task                                       |
| --- | ------------------------------------------- | ------------------------------------------------------- |
| 1   | Attacker's IP address                       | System Log Analysis                                     |
| 2   | Time when the attacker started the attack   | System Log Analysis                                     |
| 3   | MD5 of the mining program                   | Directory Inspection/File Analysis/File Integrity Check |
| 4   | MD5 of the backdoor script                  | Directory Inspection/File Analysis/File Integrity Check |
| 5   | Mining pool address (top-level domain name) | File Analysis                                           |
| 6   | Wallet address                              | File Analysis                                           |
| 7   | Manage attacker's IP                        | Risky IP Management                                     |
| 8   | Handle mining program                       | Malicious Process Handling                              |
| 9   | Handle backdoor script                      | Malicious File Handling                                 |
