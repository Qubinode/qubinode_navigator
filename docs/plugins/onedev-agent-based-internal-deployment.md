______________________________________________________________________

## layout: default title:  "Legacy: OneDev Agent-based Pipelines (Internal)" parent: Plugins nav_order: 3

OpenShift Agent Based Installer Helper

- This repo holds some utilities to easily leverage the OpenShift Agent-Based Installer. Supports bare metal, vSphere, and platform=none deployments in SNO/3 Node/HA configurations.

> **Status:** Legacy integration
>
> These instructions describe OneDev-based agent pipelines. For new work, prefer **Apache Airflow** DAGs and the AI Assistant.
>
> - Airflow overview: [AIRFLOW-INTEGRATION.md](../explanation/airflow-integration.md)
> - DAG workflows: [airflow-dag-deployment-workflows.md](../reference/airflow-dag-deployment-workflows.md)

# Prerequisites

- [OneDev - Kcli Pipelines](../plugins/onedev-kcli-pipelines.md)  - is configured and running.

**Optional: ssh into  baremetl server and run the following**

```
$ sudo kcli download image rhel8
$ sudo kcli download image rhel9
```

Reference Git Repo: [https://github.com/Red-Hat-SE-RTO/openshift-agent-install](https://github.com/Red-Hat-SE-RTO/openshift-agent-install)

## Configure pipelines

Git Repo: [https://github.com/tosin2013/kcli-pipelines.git](https://github.com/tosin2013/kcli-pipelines.git)

*Click on `import`*
![20240320093529](https://i.imgur.com/1b3zrpr.png)
*Click on `From URL`*
![20240320093616](https://i.imgur.com/pwPpEx0.png)
*Click on `Import` using kcli pipelines repo*
![20240320093704](https://i.imgur.com/EZTDdm5.png)
*click on the `tosin2013/kcli-pipelines.git` to view repos*
![20240320093809](https://i.imgur.com/MgdGkEN.png)

![20240320093959](https://i.imgur.com/pVvwaTR.png)

# Start Job

**Click .onedev-buildspec.yml**
\*Click on `Internal - OpenShift Agent Based Installer Helper`

![20240515111103](https://i.imgur.com/V6s8MnO.png)
![20240515111122](https://i.imgur.com/3fJYPIe.png)

**When vyos router is waiting to be configured run the steps below**
**Configure Networking on host**
[Configure Networking on the Host](https://github.com/tosin2013/demo-virt/blob/rhpds/demo.redhat.com/docs/step1.md)
**SSH into the bastion node to complete configuration**

```
ssh admin@baremetalhost.com
$ ls -lath vyos-config.sh
$ scp vyos-config.sh vyos@192.168.122.2:/tmp
$ ssh vyos@192.168.122.2
$ vbash /tmp/vyos-config.sh
```

**Wait for deployment to complete it should take 45 minutes to 1 hour**

**SSH into the bastion node to get the kubeconfig**

```
ssh admin@baremetalhost.com
```

To validate access to the cluster view the ha proxy stats page:

- `https://<your-hostname>:1936/haproxy?stats`

*username and password `admin`:`password`*

## Optional: Deploy OpenShift Workloads

**OpenShift Virtulization**
*Ensure you are using Openshift version 4.15 for menu option `equinix-cnv-virtualization`*

```
git clone https://github.com/tosin2013/sno-quickstarts.git
cd sno-quickstarts/gitops


# To deploy storage and tag infra nodes
./configure-redhat-labs.sh --configure-infra-nodes --configure-storage

# To deploy workloads
./configure-redhat-labs.sh
1) Exit				   8) ./aap-instance
2) ./middleware-ocpv		   9) ./acm-gitops-deployment
3) ./vmware-odf-deployment	  10) ./equinix-developer-env
4) ./kafka-plus-db		  11) ./device-edge-demos
5) ./rhel-edge-management	  12) ./developer-env
6) ./sno-ocp-virt		  13) ./standard-sno-deployment
7) ./equinix-cnv-virtualization
```

## Check the status of the deployment in ArgoCD

*NOTE: You may have to set the default stroage based on deployment Type*

```
# oc patch storageclass ocs-storagecluster-cephfs -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
# Recommened for Openshift Virtualization
# oc patch storageclass ocs-storagecluster-ceph-rbd -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```
