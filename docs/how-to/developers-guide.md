---
title: Developer's Guide
parent: How to
nav_order: 5
---

# Developer's Guide

Welcome to the Qubinode Navigator project! We are excited to have you consider contributing to our open-source project. This guide will walk you through the process of setting up your development environment, adhering to coding standards, and submitting your contributions effectively.

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
  - [Git Clone Repo](#git-clone-repo)
  - [Configure SSH](#configure-ssh)
  - [Install Ansible Navigator](#install-ansible-navigator)
- [Configure Ansible Navigator](#configure-ansible-navigator)
- [Add Hosts File](#add-hosts-file)
- [Create Requirement File for Ansible Builder](#create-requirement-file-for-ansible-builder)
- [Build the Image](#build-the-image)
- [Configure Ansible Vault](#configure-ansible-vault)
- [Install and Configure Ansible Safe](#install-and-configure-ansible-safe)
- [Configure Additional Variables](#configure-additional-variables)
- [List Inventory](#list-inventory)
- [Deploy KVM Host](#deploy-kvm-host)
- [Cleaning Up](#cleaning-up)
- [Contact](#contact)

## Introduction

Qubinode Navigator is a powerful tool designed to automate the deployment and management of virtual machines, containers, and other infrastructure resources. Whether you're experienced with open-source contributions or just getting started, we welcome your help and are here to support you throughout the process.

## Getting Started

Before diving into the development, make sure you have the necessary prerequisites:

- A Linux-based operating system (RHEL 9.2, CentOS, Rocky Linux, or Fedora)
- Git
- Basic understanding of shell scripting and Python
-

## Development Environment Setup

To get started, follow these steps to set up your development environment.

### Git Clone Repo

Firstly, you need to clone the Qubinode Navigator repository to your local machine.

```bash
git clone https://github.com/Qubinode/qubinode_navigator.git
cd $HOME/qubinode_navigator/
```

### Configure SSH

Next, configure SSH to securely connect to your development environment.

```bash
IP_ADDRESS=$(hostname -I | awk '{print $1}')
ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
ssh-copy-id $USER@${IP_ADDRESS}
```

### Install Ansible Navigator

Install Ansible Navigator, a tool to run and manage Ansible playbooks.

```bash
make install-ansible-navigator
```

If you use Red Hat Enterprise Linux with an active subscription, you might have to log into the registry first:

```bash
make podman-login
```

## Configure Ansible Navigator

Create the Ansible Navigator configuration file to manage your inventory and execution environment.

```bash
# export INVENTORY=supermicro
# cp -avi inventories/sample/ inventories/${INVENTORY}
# cat >~/.ansible-navigator.yml<<EOF
---
ansible-navigator:
  ansible:
    inventory:
      entries:
      - /home/admin/qubinode_navigator/inventories/${INVENTORY}
  execution-environment:
    container-engine: podman
    enabled: true
    environment-variables:
      pass:
      - USER
    image:  localhost/qubinode-installer:0.1.0
    pull:
      policy: missing
  logging:
    append: true
    file: /tmp/navigator/ansible-navigator.log
    level: debug
  playbook-artifact:
    enable: false
EOF
```

## Add Hosts File

Create and configure the hosts file for your inventory.

```bash
# control_user=admin
# control_host=$(hostname -I | awk '{print $1}')
echo "[control]" > inventories/${INVENTORY}/hosts
echo "control ansible_host=${control_host} ansible_user=${control_user}" >> inventories/${INVENTORY}/hosts
```

## Create Requirement File for Ansible Builder

Generate a requirements file for Ansible Builder to manage your collections and roles.

```bash
cat >ansible-builder/requirements.yml<<EOF
---
collections:
  - ansible.posix
  - containers.podman
  - community.general
  - community.libvirt
  - fedora.linux_system_roles
  - name: https://github.com/Qubinode/qubinode_kvmhost_setup_collection.git
    type: git
    version: main
roles:
  - linux-system-roles.network
  - linux-system-roles.firewall
  - linux-system-roles.cockpit
EOF
```

## Build the Image

Build the container image required for your development environment.

```bash
make build-image
```

## Configure Ansible Vault

Set up Ansible Vault for managing sensitive data.

```bash
curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
chmod +x ansible_vault_setup.sh
./ansible_vault_setup.sh
```

## Install and Configure Ansible Safe

Download and configure Ansible Safe for secure password management.

```bash
curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v0.0.6/ansiblesafe-v0.0.6-linux-amd64.tar.gz
tar -zxvf ansiblesafe-v0.0.6-linux-amd64.tar.gz
chmod +x ansiblesafe-linux-amd64
sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe

# export INVENTORY=supermicro
# ansiblesafe -f /home/${USER}/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
# ansiblesafe -f /opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
```

## Configure Additional Variables

Install additional dependencies and load required variables.

```bash
pip3 install -r requirements.txt
python3 load-variables.py
```

## List Inventory

Check the list of inventory managed by Ansible Navigator.

```bash
ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password
```

## Deploy KVM Host

Deploy the KVM host using Ansible Navigator.

```bash
$ ssh-agent bash
$ ssh-add ~/.ssh/id_rsa
$ ansible-navigator run ansible-navigator/setup_kvmhost.yml \
 --vault-password-file $HOME/.vault_password -m stdout
```

## Cleaning Up

After developing a new collection, build the image and clean up any bad builds and images.

```bash
make build-image
make remove-bad-builds
make remove-images
```

## Contact

If you have any questions or need further assistance, feel free to reach out to us:

- **GitHub Issues:** [Create an issue](https://github.com/Qubinode/qubinode_navigator/issues)
- **Discord:** [Discord](https://discord.gg/RdqJrMJudf)

Thank you for your interest in contributing to Qubinode Navigator! Together, we can build and improve a powerful tool for automating infrastructure deployment. Happy coding!

______________________________________________________________________

By following this guide, you can ensure that your contributions are well-received and integrated smoothly into the Qubinode Navigator project. We appreciate your efforts and look forward to your valuable contributions!
