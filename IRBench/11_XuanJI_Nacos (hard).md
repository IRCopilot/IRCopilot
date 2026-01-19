**Source**: [https://xj.edisec.net/challenges/34](https://xj.edisec.net/challenges/34) (XuanJi_Nacos) 
**Type**: Java Memory Web Shell Forensics
#### Keywords
- Java Forensics
- Memory Web Shell (MemShell)
- Database Forensics (Derby/Nacos)
- Shiro Vulnerability
#### Scenario
A Nacos server has been compromised. The attacker utilized a deserialization vulnerability (Shiro) to inject a **Memory Web Shell**. You need to extract the Nacos credentials from the database, identify the Shiro encryption key, and analyze/remove the resident memory trojan.
#### Sub-task LIst
|     | Task                                                           | Types of Sub-task                                      |
| --- | -------------------------------------------------------------- | ------------------------------------------------------ |
| 1   | The ciphertext value of the user password of the nacos service | Directory Inspection/Service Enumeration/File Analysis |
| 2   | What is the key of shiro                                       | Directory Inspection/Service Enumeration/File Analysis |
| 3   | The kernel version of the target machine                       | System Information Gathering                           |
| 4   | Delete the backdoor user                                       | Permission Review and Management                       |
| 5   | Weak password repair                                           | Other Response/Vulnerability Patching                  |
| 6   | Handle trojan                                                  | Malicious File Handling                                |
