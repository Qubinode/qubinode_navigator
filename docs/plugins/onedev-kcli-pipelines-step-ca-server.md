______________________________________________________________________

## layout: default title:  "Legacy: Deploy Step CA Server using OneDev Kcli Pipelines" parent: Plugins nav_order: 3

## Deploy Step CA Server using Kcli Pipelines

> **Status:** Legacy integration
>
> This guide describes Step CA deployment via OneDev Kcli pipelines. For new environments, consider modelling these steps as an **Airflow DAG** managed by the Airflow sidecar.
>
> - Airflow overview: [AIRFLOW-INTEGRATION.md](../explanation/airflow-integration.md)
> - DAG workflows: [airflow-dag-deployment-workflows.md](../reference/airflow-dag-deployment-workflows.md)

## Requirements

- [OneDev - Kcli Pipelines](../plugins/onedev-kcli-pipelines.md)  - is configured and running.

**ssh into baremetl server and run the following**

```
$ sudo kcli download image rhel8
$ sudo kcli download image rhel9
```

## Example pipelines

Trigger kcli-pipelines to deploy VMs on Baremetal server using OneDev pipelines.

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
![20240416105606](https://i.imgur.com/YxCRKv7.png)

\*Click on `step-ca server`
![20240416105655](https://i.imgur.com/6DR9I3D.png)

- *GIT_REPO  Flag allow us to set the git repo for the step-ca server*
- *DOMAIN  Flag allow us to set the domain for the step-ca server*
- *COMMUNITY_VERSION  Flag allow us to deploy on rhel9 if set to false and centos 9 Streams if set to true*
- *INITIAL_PASSWORD  Flag allow us to set the initial password for the step-ca server*

![20240416163140](https://i.imgur.com/J9yPo0r.png)

Access step-ca server using

```
$ sudo kcli ssh step-ca-server
$ sudo su -
$ systemctl status step-ca
$ cat /var/log/step-ca.log
```

Extend the step-ca server certificate maxTLSCertDuration `2000h` and defaultTLSCertDuration `2000h`

```
jq '.authority.provisioners[0].claims = {"minTLSCertDuration": "5m", "maxTLSCertDuration": "2000h", "defaultTLSCertDuration": "2000h"}' .step/config/ca.json > .step/config/ca.json.tmp
mv .step/config/ca.json .step/config/ca.json.bak
mv .step/config/ca.json.tmp .step/config/ca.json
systemctl restart step-ca
systemctl status step-ca
```

Allow jumpbox to use root certificate

```
$ sudo su - remoteuser
$ /opt/kcli-pipelines/step-ca-server/register-step-ca.sh  <ca-url> <fingerprint>
```

## Configure Certs on OpenShift

*run on jumpbox or baremetal host connected to openshift cluster*

```
$ curl -OL https://raw.githubusercontent.com/tosin2013/openshift-4-deployment-notes/master/pre-steps/configure-openshift-packages.sh
$ chmod +x configure-openshift-packages.sh
$ ./configure-openshift-packages.sh -i
$ oc login --token=sha256~QCHANGEME --server=https://api.changeme.changeme.com:6443
$ curl -OL https://raw.githubusercontent.com/tosin2013/openshift-4-deployment-notes/master/post-steps/configure-ocp-certs-stepca.sh
$ chmod +x configure-ocp-certs-stepca.sh
$ ./configure-ocp-certs-stepca.sh
```
