______________________________________________________________________

## layout: default title:  "Legacy: OneDev kcli-openshift4-baremetal (Internal)" parent: Plugins nav_order: 3

This repository provides a plan which deploys a vm where:

- openshift-baremetal-install is downloaded with the specific version and tag specified (and renamed openshift-install)
- stop the nodes to deploy through redfish
- launch the install against a set of baremetal nodes. Virtual ctlplanes and workers can also be deployed
- OpenShift is deployed using the ipi method

> **Status:** Legacy integration
>
> These pipelines were designed around OneDev. For new baremetal OpenShift deployments, represent this flow as **Airflow DAGs** and manage it via the Airflow integration.
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

Reference Git Repo: [https://github.com/karmab/kcli-openshift4-baremetal](https://github.com/karmab/kcli-openshift4-baremetal)

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
![20240429154854](https://i.imgur.com/ca9lFEk.png)

*Click on `kcli-openshift4-baremetal` - Deploy OpenShift on KVM*
![20240412135736](https://i.imgur.com/B4puUCU.png)
![20240412135958](https://i.imgur.com/yL6hiQD.png)

**Wait for deployment to complete it should take 45 minutes to 1 hour**
![20240323194135](https://i.imgur.com/dsLFUqO.png)

![20240415113845](https://i.imgur.com/N0DXbE3.png)

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
