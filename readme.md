sudo cp /home/user3t/Workspace/projects/in-process/kienvq/system32.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable system32.service
sudo systemctl start system32.service
sudo systemctl status system32.service