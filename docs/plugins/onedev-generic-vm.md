______________________________________________________________________

## layout: default title:  "Legacy: OneDev - Deploying Generic VMs" parent: Plugins nav_order: 3

## Kcli Pipelines using OneDev

> **Status:** Legacy integration
>
> This guide describes historical OneDev-based VM deployment pipelines. For new environments, use Apache Airflow DAGs and the AI Assistant to orchestrate deployments.
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
![20240323193344](https://i.imgur.com/mi3udC6.png)

*Click on `Deploy VM` - Deploy FreeIPA VM first this will allow you to deploy the other vms*
![20240320100623](https://i.imgur.com/kigo2L3.png)

**Current List of Deployable VMs after FreeIPA Deployment**
![20240320101445](https://i.imgur.com/IXsGQg3.png)
