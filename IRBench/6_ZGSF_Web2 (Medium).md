**Source**: [https://pan.quark.cn/s/4b6dffd0c51a](https://pan.quark.cn/s/4b6dffd0c51a) (ZGSF_Web2) 
**Type**: Web Compromise & Intranet Pivoting
#### Keywords
- Web Log Analysis
- Webshell Analysis
- Hidden Account
- Intranet Proxy (FRP) Analysis
#### Scenario
A Windows web server has been compromised. The attacker uploaded a webshell, created a hidden system account, and deployed a reverse proxy tool (FRP) to penetrate the intranet. You need to identify the attacker's entry point, analyze the proxy configuration, and remove the threats.
#### Sub-task LIst
|     | Task                                                           | Types of Sub-task                            |
| --- | -------------------------------------------------------------- | -------------------------------------------- |
| 1   | The attacker's two IP addresses                                | Application Log Analysis/System Log Analysis |
| 2   | The attacker's webshell file name                              | Directory Inspection/File Analysis           |
| 3   | The attacker's webshell password                               | File Analysis                                |
| 4   | The attacker's hidden username                                 | Directory Inspection/Account Security Review |
| 5   | The attacker's fake QQ number                                  | Directory Inspection                         |
| 6   | The attacker's fake server IP address                          | Directory Inspection/File Analysis           |
| 7   | The server port used by the attacker to penetrate the intranet | Directory Inspection/File Analysis           |
| 8   | Manage the attacker's two IP addresses                         | Risky IP Management                          |
| 9   | Handle webshell                                                | Malicious File Handling                      |
| 10  | Handle frp file                                                | Malicious File Handling                      |
| 11  | Delete unauthorized user                                       | Permission Review and Management             |
