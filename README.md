# 👋 IRCopilot: Automated Incident Response with Large Language Models

Source code for paper "IRCopilot: Automated Incident Response with Large Language Models", the code will be relased after the publication of the paper.

#### Benchmark
##### benchmark info
| Target Name                     | Difficulty | OS      | Number of Tasks |     | Source                                            |
| ------------------------------- | ---------- | ------- | --------------- | --- | ------------------------------------------------- |
| Investigating Windows           | Easy       | Windows | 22              |     | https://tryhackme.com/r/room/investigatingwindows |
| Linux1                          | Easy       | Linux   | 7               |     | https://pan.quark.cn/s/4b6dffd0c51a               |
| Web1                            | Easy       | Windows | 7               |     | https://pan.quark.cn/s/4b6dffd0c51a               |
| Tardigrade                      | Medium     | Linux   | 15              |     | https://tryhackme.com/r/room/tardigrade           |
| VulnTarget-n-Ransomware         | Medium     | Linux   | 6               |     | https://xj.edisec.net/challenges/84               |
| Web2                            | Medium     | Windows | 11              |     | https://pan.quark.cn/s/4b6dffd0c51a               |
| Web3                            | Medium     | Windows | 11              |     | https://pan.quark.cn/s/4b6dffd0c51a               |
| Windows Black Pages & Tampering | Medium     | Windows | 10              |     | https://xj.edisec.net/challenges/51               |
| Windows Miner                   | Medium     | Windows | 9               |     | https://pan.quark.cn/s/4b6dffd0c51a               |
| Linux2                          | Hard       | Linux   | 11              |     | https://pan.quark.cn/s/4b6dffd0c51a               |
| Memory Trojan Analysis - Nacos  | Hard       | Linux   | 6               |     | https://xj.edisec.net/challenges/34               |
| Where 1S tHe Hacker             | Hard       | Windows | 15              |     | https://xj.edisec.net/challenges/63               |
|                                 |            |         |                 |     |                                                   |
| Total                           |            |         | 130             |     |                                                   |

##### Summarized 27 Types of Sub-tasks in the Proposed Incident Response Benchmark
| **Phase**     | **Technique**                            | **Description**                                                                                                               |
| ------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Detection** | System Information Gathering             | Includes operating system identification, network configuration analysis, hardware information gathering, etc.                |
|               | Open Port Identification                 | Detect open network ports on the target system.                                                                               |
|               | Service Enumeration                      | Identify and analyze running services to uncover version details and vulnerabilities.                                         |
|               | Directory Inspection                     | Examine key directories and hidden files for unusual activity.                                                                |
|               | Account Security Review                  | Audit user account permissions and identify unauthorized accounts or backdoors.                                               |
|               | File Integrity Check                     | Monitor file hashes to detect unauthorized changes.                                                                           |
|               | Other Detections                         | Inspect other vulnerable areas of the system, such as the registry, etc.                                                      |
| **Response**  | Historical Command and Behavior Analysis | Review user commands and system behaviors to detect abnormal operations.                                                      |
|               | Permission Review and Management         | Audit system and application permissions to enforce least-privilege principles and manage risky permissions.                  |
|               | File Analysis                            | Inspect system files and source code for vulnerabilities or malicious content.                                                |
|               | Malicious File Handling                  | Identify, isolate, and remove malicious files to prevent further damage.                                                      |
|               | Startup Item Analysis                    | Review startup items for unauthorized programs or scripts.                                                                    |
|               | Scheduled Task Analysis                  | Analyze the system's scheduled tasks settings to identify possible malicious or planned tasks.                                |
|               | Anomaly Behavior Response                | Respond to abnormal system or user behaviors to contain potential threats.                                                    |
|               | Memory and Process Analysis              | Examine memory and processes to identify abnormal or malicious activity.                                                      |
|               | Malicious Process Handling               | Terminate malicious processes to mitigate ongoing threats.                                                                    |
|               | System Log Analysis                      | Analyze system logs for signs of compromise, unauthorized access, or suspicious activities.                                   |
|               | Application Log Analysis                 | Review application logs for exploitation attempts or unusual behavior.                                                        |
|               | Network Traffic Analysis                 | Analyze network traffic to identify suspicious communication or data exfiltration.                                            |
|               | Risky IP Management                      | Block or monitor traffic from known malicious or suspicious IP addresses.                                                     |
|               | Database Analysis                        | Analyze databases for security vulnerabilities, data leaks, or unauthorized access.                                           |
|               | Other Responses                          | Conduct additional response activities, such as analyzing virtualization environments or reviewing container security.        |
| **Recovery**  | System Recovery                          | Restore the system to a stable state after failures, malware, or misconfigurations.                                           |
|               | Data Recovery                            | Recover lost or corrupted data from backups or damaged media.                                                                 |
|               | Service Recovery                         | Restore key services and applications to minimize downtime.                                                                   |
|               | Vulnerability Patching                   | Apply patches to fix vulnerabilities and prevent recurrence of attacks.                                                       |
|               | Other Recoveries                         | Additional recovery methods, such as network recovery and permission reset, to address various aspects of system restoration. |




<!--
**IRCopilot/IRCopilot** is a ✨ _special_ ✨ repository because its `README.md` (this file) appears on your GitHub profile.

Here are some ideas to get you started:

- 🔭 I’m currently working on ...
- 🌱 I’m currently learning ...
- 👯 I’m looking to collaborate on ...
- 🤔 I’m looking for help with ...
- 💬 Ask me about ...
- 📫 How to reach me: ...
- 😄 Pronouns: ...
- ⚡ Fun fact: ...
-->
