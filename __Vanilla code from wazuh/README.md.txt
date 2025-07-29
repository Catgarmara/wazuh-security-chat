Replace <USERNAME> and <PASSWORD> with your preferred username and password for accessing the LLM chatbot.

username="<USERNAME>"
password="<PASSWORD>"
ssh_username = "<SSH_USERNAME>"
ssh_password = "<SSH_PASSWORD>"

To run it in a dedicated host with GPU

The script also supports running on a remote system rather than the Wazuh server. To run the script from a remote server, an SSH user is required to read the logs from the Wazuh server. The following steps are required to run the script from a remote server.

1. Create an SSH user on the Wazuh server. An existing SSH user can also be used:
adduser <SSH_USERNAME>

Replace <SSH_USERNAME> with the username of the SSH user.

2. Add the newly created or existing user to the wazuh group. This is required to give the user appropriate permissions to read the Wazuh archive files:
usermod -aG wazuh <SSH_USERNAME>

3. Replace <SSH_USERNAME> and <SSH_PASSWORD> in the threat_hunter.py script with the username and password of the SSH user on the Wazuh server..

4. Run the threat_hunter.py script with the -H <WAZUH_SERVER_IP> argument on the remote server. For example, python3 threat_hunter.py -H 192.168.8.100:
python3 threat_hunter.py -H <WAZUH_SERVER_IP>