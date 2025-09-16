## VM Setup

Manually created on Azure.

### Install Python

- $ sudo apt update
- $ sudo apt install -y git python3 python3-venv python3-pip

### Install Git

- $ sudo apt install git -y

### Create Application Directory

- $ mkdir -p ~/apps/square-combo

### Create SSH Key for Git

- $ ssh-keygen -t rsa -b 4096 -C "deploy@square-combo”

**→ Get the public key generated and save in GitHub deploy keys**

### Clone the project into app directory

- $ git clone [git@github.com](mailto:git@github.com):davaico/square-combo.git .

### Initialize Application

- $ python3 -m venv venv
- $ source venv/bin/activate
- $ pip install -r requirements.txt

### Create service file for start / restart application

- $ sudo nano /etc/systemd/system/square-combo.service
- $ sudo systemctl daemon-reload
- $ sudo systemctl enable square-combo

### Start Application

- $ sudo systemctl start square-combo

### Setup Nginx + Certificate

- $ sudo apt install -y nginx certbot python3-certbot-nginx
- $ sudo nano /etc/nginx/sites-available/square-combo
- $ sudo ln -s /etc/nginx/sites-available/square-combo /etc/nginx/sites-enabled/
- $ sudo nginx -t
- $ sudo systemctl restart nginx
- $ sudo certbot --nginx -d [squarecombo.com](http://squarecombo.com/)

### Create .env file

- $ nano /home/davaiadmin/apps/square-combo/.env

### Create .db file

- $ /home/davaiadmin/apps/square-combo/venv/bin/python python -m database.__**init__**
