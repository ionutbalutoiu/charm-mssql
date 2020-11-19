# Deployment Preparation

This charm is deployed on top of Kubernetes. It uses the operator framework,
and it needs to be built first. If you are deploying from the charm store,
this step is not necessary. If you are cloning from source, you need to:

* Install `charmcraft` from snap store:
    ```
    sudo snap install charmcraft --beta
    ```

* Build the charm:
    ```
    cd <charm_repo_dir>
    charmcraft build -v
    ```

    The charm build artifact will be `mssql.charm`, and we will use this to
    deploy it.

# MicroK8s and Juju Setup

```
sudo snap install microk8s --classic
microk8s.enable dns dashboard registry storage

sudo snap install juju --classic
juju bootstrap microk8s
juju add-model mssql
juju deploy ./mssql.charm --config accept-eula=true
```

When deploying locally on top of MicroK8s, the service is reachable over
the port-forwarding configuration. For example, for a service exposed like
this:
```
NAMESPACE NAME           TYPE          CLUSTER-IP     EXTERNAL-IP  PORT(S)
mssql     service/mssql  LoadBalancer  10.152.183.16  <pending>    1443:32542/TCP
```

And a host of IP `192.168.1.75`, then the service would be reachable at
`192.168.1.75:32542`. 

# Microsoft SQL Server Utility

To communicate with the database, the `sqlcmd` utility comes handy.
Instructions to install it on Ubuntu are available [here](https://docs.microsoft.com/en-us/sql/linux/sql-server-linux-setup-tools?view=sql-server-ver15#ubuntu).

An example of command to connect to the database would be:
```
sqlcmd -S 192.168.1.75,32038 -U SA -P "<SA_PASSWORD>"
```

To find out the `SA` password, run the following command:
```
juju exec --operator --unit mssql/leader leader-get
```
