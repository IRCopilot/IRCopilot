# 👋 IRCopilot: Automated Incident Response with Large Language Models

Source code for paper "IRCopilot: Automated Incident Response with Large Language Models", the code will be relased after the publication of the paper.

### Benchmark
#### [benchmark info](./Benchmark_Information/)
Click on the target name to get the sub-task list
|     | Target Name                                                                                                            | Difficulty | OS      | Number of Tasks | Source                                            |
| --- | ---------------------------------------------------------------------------------------------------------------------- | ---------- | ------- | --------------- | ------------------------------------------------- |
| 1   | [Investigating Windows](./Benchmark_Information/1_TryHackMe_InvestigatingWindows%20(Easy).md)                          | Easy       | Windows | 22              | https://tryhackme.com/r/room/investigatingwindows |
| 2   | [Linux1](./Benchmark_Information/2_ZGSF_Linux1%20(Easy))                                                               | Easy       | Linux   | 7               | https://pan.quark.cn/s/4b6dffd0c51a               |
| 3   | [Web1](./Benchmark_Information/3_ZGSF_Web1%20(Easy))                                                                   | Easy       | Windows | 7               | https://pan.quark.cn/s/4b6dffd0c51a               |
| 4   | [Tardigrade](./Benchmark_Information/4_TryHackMe_Tardigrade%20(Medium))                                                | Medium     | Linux   | 15              | https://tryhackme.com/r/room/tardigrade           |
| 5   | [VulnTarget-n-Ransomware](./Benchmark_Information/5_XuanJI_VulnTarget-n-Ransomware%20(Medium))                         | Medium     | Linux   | 6               | https://xj.edisec.net/challenges/84               |
| 6   | [Web2](./Benchmark_Information/6_ZGSF_Web2%20(Medium))                                                                 | Medium     | Windows | 11              | https://pan.quark.cn/s/4b6dffd0c51a               |
| 7   | [Web3](./Benchmark_Information/7_ZGSF_Web3%20(Medium))                                                                 | Medium     | Windows | 11              | https://pan.quark.cn/s/4b6dffd0c51a               |
| 8   | [Windows Black Pages & Tampering](./Benchmark_Information/8_XuanJI_Windows%20Black%20Pages%20&%20Tampering%20(medium)) | Medium     | Windows | 10              | https://xj.edisec.net/challenges/51               |
| 9   | [Windows Miner](./Benchmark_Information/9_ZGSF_WindowsMiner%20(Medium))                                                | Medium     | Windows | 9               | https://pan.quark.cn/s/4b6dffd0c51a               |
| 10  | [Linux2](./Benchmark_Information/10_ZGSF_Linux2%20(Hard))                                                              | Hard       | Linux   | 11              | https://pan.quark.cn/s/4b6dffd0c51a               |
| 11  | [Memory Trojan Analysis - Nacos](./Benchmark_Information/11_XuanJI_Nacos%20(hard))                                     | Hard       | Linux   | 6               | https://xj.edisec.net/challenges/34               |
| 12  | [Where 1S tHe Hacker](./Benchmark_Information/12_XuanJI_Where-1S-tHe-Hacker%20(hard))                                  | Hard       | Windows | 15              | https://xj.edisec.net/challenges/63               |
|     |                                                                                                                        |            |         |                 |                                                   |
|     | Total                                                                                                                  |            |         | 130             |                                                   |

#### Summarized 27 Types of Sub-tasks in the Proposed Incident Response Benchmark
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

#### Data Contamination Mitigation. [Have LLMs been trained on benchmark tests or writeups?](./Have%20LLMs%20been%20trained%20on%20benchmark%20tests%20or%20writeups)
IRCopilot is built based on LLMs, recognizing that cases or writeups on these platforms may already be included in LLM training data, which can potentially bias experimental results. To address concerns about data contamination in LLMs/IRCopilot, we implement three measures. First, we verify whether the LLMs had undergone targeted training by directly querying them for detailed information about specific cases, and we publish the relevant content on our Anonymous Github. Second, during the benchmark selection process, we prioritize cases with more recent publication dates, which are most likely to fall outside the scope of the LLMs’ training data. Finally, since IRCopilot has the ability to display each step of its reasoning process, we confirm through an examination of its reasoning paths that it lacks prior knowledge of the cases. Furthermore, real-world cases in practicality study further demonstrated that, even without targeted training, IRCopilot shows significant feasibility and effectiveness in real-world applications.

### Prompt
[Prompt of IRCopilot](./prompt_class_IRCopilot_en.py), and the code will be relased after the publication of the paper.


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
