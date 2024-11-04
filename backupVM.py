import os
import subprocess
import datetime
import shutil
import glob
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Diretório onde os backups são armazenados
backup_directory = "/root/backup_vms"
remote_name = "googleDrive"  # Nome do remote configurado no rclone
drive_directory = "BkpAthenaSquadDev"  # Pasta no Google Drive

# IDs das VMs que deseja fazer backup
vm_ids = ["103"]  # Adicione mais IDs conforme necessário

# Configurações de e-mail
smtp_server = "smtp.seuprovedor.com"  # Substitua pelo servidor SMTP
smtp_port = 587  # Porta do servidor SMTP
smtp_user = "seuemail@dominio.com"  # Seu endereço de e-mail
smtp_password = "sua_senha"  # Sua senha de e-mail
destinatarios = ["destinatario1@dominio.com", "destinatario2@dominio.com"]  # Lista de e-mails para enviar

def enviar_email(vm_id):
    """Envia um e-mail de conclusão de backup com sucesso."""
    assunto = f"Backup da VM {vm_id} concluído com sucesso"
    corpo = f"O backup da VM {vm_id} foi realizado com sucesso e enviado para o Google Drive."

    # Criando a mensagem de e-mail
    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = assunto
    msg.attach(MIMEText(corpo, "plain"))

    try:
        # Conectando ao servidor SMTP e enviando o e-mail
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Ativa a criptografia TLS
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        print(f"E-mail enviado com sucesso para: {', '.join(destinatarios)}")
    except Exception as e:
        print(f"Falha ao enviar e-mail: {e}")

# Criar backups das VMs
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
for vm_id in vm_ids:
    print(f"Criando backup da VM {vm_id}...")
    proxmox_backup_command = f"vzdump {vm_id} --mode snapshot --compress gzip --dumpdir {backup_directory}"
    subprocess.run(proxmox_backup_command, shell=True, check=True)
    
    # Procurar o arquivo gerado
    original_backup = glob.glob(os.path.join(backup_directory, f"vzdump-qemu-{vm_id}-*.vma.gz"))
    if original_backup:
        original_backup_path = original_backup[0]
        # Novo nome do arquivo com o timestamp
        new_backup_path = os.path.join(backup_directory, f"vzdump-qemu-{vm_id}-{timestamp}.vma.gz")
        os.rename(original_backup_path, new_backup_path)
        print(f"Backup da VM {vm_id} renomeado para: {new_backup_path}")
    else:
        print(f"Arquivo de backup original para VM {vm_id} não encontrado.")
        continue

    # Verificar o backup antes de enviar ao Google Drive
    temp_extract_dir = os.path.join(backup_directory, f"temp_extract_{vm_id}")
    os.makedirs(temp_extract_dir, exist_ok=True)

    gunzip_command = f"gunzip -c {new_backup_path} > {temp_extract_dir}/backup_{vm_id}.vma"
    try:
        print(f"Verificando backup da VM {vm_id} descomprimindo o arquivo .vma.gz...")
        subprocess.run(gunzip_command, shell=True, check=True)
        print("Descompressão realizada com sucesso. O backup está íntegro.")
        
        shutil.rmtree(temp_extract_dir)
        print("Arquivos descomprimidos removidos.")

        # Upload do arquivo para o Google Drive
        upload_command = f"rclone copy {new_backup_path} {remote_name}:{drive_directory}"
        print(f"Subindo {new_backup_path} para o Google Drive...")
        subprocess.run(upload_command, shell=True, check=True)
        print("Upload realizado com sucesso.")

        # Excluir o arquivo local após o upload
        os.remove(new_backup_path)
        print(f"Arquivo {new_backup_path} excluído com sucesso.")

        # Enviar e-mail de conclusão
        enviar_email(vm_id)

    except subprocess.CalledProcessError:
        print("Falha na descompressão. O arquivo de backup pode estar corrompido.")
