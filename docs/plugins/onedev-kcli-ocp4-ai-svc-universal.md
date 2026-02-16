______________________________________________________________________

## layout: default title:  "Legacy: OneDev OpenShift Assisted Installer (Universal)" parent: Plugins nav_order: 3

This repository provides a plan which deploys a vm where:

- openshift-baremetal-install is downloaded with the specific version and tag specified (and renamed openshift-install)
- stop the nodes to deploy through redfish
- launch the install against a set of baremetal nodes. Virtual ctlplanes and workers can also be deployed

> **Status:** Legacy integration
>
> This universal installer workflow is still documented for OneDev users. New deployments should converge on **Airflow DAGs** and the AI Assistant for orchestration.
>
> - Airflow overview: [AIRFLOW-INTEGRATION.md](../explanation/airflow-integration.md)
> - DAG workflows: [airflow-dag-deployment-workflows.md](../reference/airflow-dag-deployment-workflows.md)

# Prerequisites

- [OneDev - Kcli Pipelines](../plugins/onedev-kcli-pipelines.md)  - is configured and running.

**ssh into  baremetl server and run the following**

```
$ sudo kcli download image rhel8
$ sudo kcli download image rhel9
```

Reference Git Repo: [https://github.com/Red-Hat-SE-RTO/ocp4-ai-svc-universal](https://github.com/Red-Hat-SE-RTO/ocp4-ai-svc-universal)

## Configure pipelines

Git Repo: [https://github.com/Red-Hat-SE-RTO/ocp4-ai-svc-universal.git](https://github.com/Red-Hat-SE-RTO/ocp4-ai-svc-universal.git)

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
![20240323193344](https://i.imgur.com/mi3udC6.png)

*Click on `kcli-openshift4-baremetal` - Deploy OpenShift on KVM*
![20240323193525](https://i.imgur.com/ZmyBOo6.png)
![20240323193635](https://i.imgur.com/qOR2ZO9.png)

**Wait for deployment to complete it should take 45 minutes to 1 hour**
![20240323194135](https://i.imgur.com/dsLFUqO.png)

![20240323213443](https://i.imgur.com/NnqvNFx.png)

*Click on `Deploy VM` - Deploy FreeIPA VM first this will allow you to access the vms*
![20240320100623](https://i.imgur.com/kigo2L3.png)

**Configure DNS**

```
$ /opt/kcli-pipelines/configure-dns.sh
```

**SSH into the bastion node to get the kubeconfig**

```
ssh admin@baremetalhost.com
```

**ssh into jump host**

```
sudo kcli list vms
sudo kcli ssh lab-installer
[centos@lab-installer ~]$ sudo su -
[root@lab-installer ~]# ls
bin                  machineconfigs  openshift_pull.json  version.txt
cluster_ready.txt    manifests       original-ks.cfg
install-config.yaml  ocp             scripts
[root@lab-installer ~]# cat ocp/.openshift_install.log
```

![20240324151019](https://i.imgur.com/ASoWhOt.png)

## Option Deploy OpenShift Workloads

**OpenShift Virtulization**
*Ensure you are using Openshift version 4.15 for menu option 5*

```
git clone https://github.com/tosin2013/sno-quickstarts.git
cd sno-quickstarts/gitops
./configure-redhat-labs.sh

1) ./aap-instance		   7) ./kafka-plus-db
2) ./acm-gitops-deployment	   8) ./middleware-ocpv
3) ./developer-env		   9) ./rhel-edge-management
4) ./device-edge-demos		  10) ./sno-ocp-virt
5) ./equinix-cnv-virtualization	  11) ./standard-sno-deployment
6) ./equinix-developer-env	  12) ./vmware-odf-deployment
#? 8
```

## Check the status of the deployment in ArgoCD

*NOTE: You may have to set the default stroage based on deployment Type*

```
# oc patch storageclass ocs-storagecluster-cephfs -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
# Recommened for Openshift Virtualization
# oc patch storageclass ocs-storagecluster-ceph-rbd -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```
