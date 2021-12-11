when we install k8s we will be installing below k8s components

1. An API-Server --> Acts as front-end for kubernetes.The Users, Management Devices, Commandline  interfaces all talk to the API Server to interact with kubernetes cluster.
2. An ETCD service --> Distributed Reliable key-value store info about multiple clusters and resposible maintain locks as well.
3. A Kubelet service.
4. A Container Runtime.
5. Controllers.
6. Schedulers --> Distribute containers or apps across multiple nodes, it looks for newly created containers and assigns them to nodes.

k8s does container orchestration.
