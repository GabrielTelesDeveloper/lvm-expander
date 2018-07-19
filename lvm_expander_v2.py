#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

"""

from lvm4py import LVM
import os
from subprocess import call, check_output
from datetime import datetime, timedelta
import time
import re
import sys
import argparse

EXTEND_TIME_THRESHOLD_MINUTES = 1440 
THRESHOLD_REGISTER_FILE_PATH = '/tmp/lvm_expander_register'
#PARTITION_FDISK_STRING = r'o\nn\np\n1\n\n\nt\n8e\nw'

lvm = LVM()
now = datetime.now()

parser = argparse.ArgumentParser(description='Expandir disco automaticamente')
parser.add_argument('-m','--ponto_de_montagem', type=str, metavar='', required=True, help='Informar o ponto de montagem')
parser.add_argument('-q','--qtd', type=int, metavar='', required=True, help='Quantidade a ser expandida')
parser.add_argument('-d','--device_path', type=str, metavar='', required=False, help='Path para o device a ser utilizado como PV')
args = parser.parse_args()

# verifica se eh ponto de montagem
def is_mp(ponto_de_montagem):
    return os.path.ismount(ponto_de_montagem)
        
# estende o vg com o device identificado pelo path
def extend_vg(vg_name, device_path):
    os.system('vgextend %s %s' % (vg_name, device_path))

# estende o mp
def extend_mp(device_path, qtd):
    os.system("lvextend -L +" + str(qtd) + "g " + device_path)
    os.system("resize2fs " + device_path)

# verifica se pode executar o script novamente
def is_time_to_execute(device_path):
    if os.path.exists(THRESHOLD_REGISTER_FILE_PATH):
        with open(THRESHOLD_REGISTER_FILE_PATH,'r') as arq:
            for linha in arq.readlines():
                linha = linha.strip()
                regex = '%s;(.+)' % (device_path)
                m = re.search(regex, linha)

                if m:
                    last_execution_time_string = m.group(1)
                    last_execution_timestamp = datetime.strptime(last_execution_time_string, '%Y-%m-%d %H:%M:%S.%f')
                    permit_execution_timestamp = last_execution_timestamp + timedelta(minutes = EXTEND_TIME_THRESHOLD_MINUTES)
                    
                    return now > permit_execution_timestamp

    return True

# atualiza o registro de execucao
def update_execution_register(device_path):
    
    report_content = dict()
    
    if os.path.exists(THRESHOLD_REGISTER_FILE_PATH):
        with open(THRESHOLD_REGISTER_FILE_PATH,'r') as arq:
            for linha in arq.readlines():
                linha = linha.strip()
                data = linha.split(';')
                
                report_content[data[0]] = data[1]
    
    report_content[device_path] = str(now)

    with open(THRESHOLD_REGISTER_FILE_PATH, 'w') as arq:
        for key in report_content.keys():
            arq.write(key + ";" + report_content[key] + "\n")
            
# verifica se tem espaco disponivel no VG
def vg_has_space_available(vg_name, qtd):
    vg = lvm.get_vg(vg_name)
    free_string = vg.free('G')
    free_integer = int(free_string.split(',')[0])
    return int(qtd) < free_integer

# recupera o device e o nome do vg
def get_lvm_data(ponto_de_montagem):
    
    device_path = check_output("grep \" " + ponto_de_montagem + " \" /etc/fstab | awk '{print $1}'", shell=True)
    device_path = device_path.strip()
    vgs = re.split(r'[/,-]', device_path)
    vg_name = vgs[3]

    if call("sudo vgs | grep " + vg_name + " > /dev/null", shell=True) == 0:
        return dict(
            device_path= device_path,
            vg_name= vg_name, 
        )

if __name__ == '__main__':
    
    try:

        # verifica se o tamanho maximo de 100GB foi obedecido. Sai do script, caso contrario
        if (args.qtd > 100):
            sys.exit('max expansion size is 100 GBs')
        
        # verifica se eh Mount Point. Sai do script, caso contrario
        if (not is_mp(args.ponto_de_montagem)):
            sys.exit('%s is not a valid mount point' % (args.ponto_de_montagem))

        # recupera o dict com os dados do LV (device path, VG e LV). Sai do script, caso contrario
        lvm_data = get_lvm_data(args.ponto_de_montagem)

        if not lvm_data:
            sys.exit('%s is not a lvm' % (args.ponto_de_montagem))

        # verifica se pode executar o script por causa do limite de tempo. 
        if not is_time_to_execute(lvm_data['device_path']):
            sys.exit('you cannot extend the %s again' % (lvm_data['device_path']))

        # adiciona o disco no VG, se o device tiver sido informado
        if (args.device_path):
            extend_vg(lvm_data['vg_name'], args.device_path)

        # verifica se tem espaco no VG para estender o disco
        if not vg_has_space_available(lvm_data['vg_name'], args.qtd):
            print('There is not enough space available in %s' % (lvm_data['vg_name']))
            sys.exit(4)

        # estende o mount point
        extend_mp(lvm_data['device_path'], args.qtd)

        # registra a ultima execucao da extencao
        update_execution_register(lvm_data['device_path'])

    except Exception as erro:
        print(erro)
