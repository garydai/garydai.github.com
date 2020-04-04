---
date: 2019-6-15
layout: default

title: zookeeper

---

# zookeeper

创建唯一顺序id怎么做到的

高性能、高可用、写操作顺序性

## 常用命令

ls /

create /test 1

set /test 2

get /test

delete

rmr

## 节点
1. 持久节点

creste 

2. 临时节点

create -e

3. 持久顺序节点

create -s

4. 临时顺序节点

create -s -e


## 存储
存放在内存

树形存储结构

## 集群
leader

follower

learner

ack过半

zab协议

一个节点默认最大数据量是1M
## 端口
同步端口

选举端口

## 持久化


![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/zookeeper.png)


![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/zookeeper2.png)

## 服务端

### 入口

org.apache.zookeeper.server.quorum.QuorumPeerMain#main

org.apache.zookeeper.server.quorum.QuorumPeerMain#initializeAndRun

```java
protected void initializeAndRun(String[] args)
    throws ConfigException, IOException, AdminServerException
{
    QuorumPeerConfig config = new QuorumPeerConfig();
    if (args.length == 1) {
        config.parse(args[0]);
    }
		
  	// 清理线程
    // Start and schedule the the purge task
    DatadirCleanupManager purgeMgr = new DatadirCleanupManager(config
            .getDataDir(), config.getDataLogDir(), config
            .getSnapRetainCount(), config.getPurgeInterval());
    purgeMgr.start();

    if (args.length == 1 && config.isDistributed()) {
      	// 运行服务
        runFromConfig(config);
    } else {
        LOG.warn("Either no config or no quorum defined in config, running "
                + " in standalone mode");
        // there is only server in the quorum -- run as standalone
        ZooKeeperServerMain.main(args);
    }
}
```

org.apache.zookeeper.server.quorum.QuorumPeerMain#runFromConfig

```java
public void runFromConfig(QuorumPeerConfig config)
        throws IOException, AdminServerException
{
  
  
    if (config.getClientPortAddress() != null) {
      // 实例化nio server factory，NIOServerCnxnFactory
      cnxnFactory = ServerCnxnFactory.createFactory();
      // 创建接受用户请求的io的相关线程
      cnxnFactory.configure(config.getClientPortAddress(),
                            config.getMaxClientCnxns(),
                            config.getClientPortListenBacklog(), false);      
    }
  
  
    // 启动集群之间的交互（选举等）io各个线程
    quorumPeer.start();
}
```

org.apache.zookeeper.server.NIOServerCnxnFactory#configure

```java
public void configure(InetSocketAddress addr, int maxcc, int backlog, boolean secure) throws IOException {
    if (secure) {
        throw new UnsupportedOperationException("SSL isn't supported in NIOServerCnxn");
    }
    configureSaslLogin();

    maxClientCnxns = maxcc;
    sessionlessCnxnTimeout = Integer.getInteger(
        ZOOKEEPER_NIO_SESSIONLESS_CNXN_TIMEOUT, 10000);
    // We also use the sessionlessCnxnTimeout as expiring interval for
    // cnxnExpiryQueue. These don't need to be the same, but the expiring
    // interval passed into the ExpiryQueue() constructor below should be
    // less than or equal to the timeout.
    cnxnExpiryQueue =
        new ExpiryQueue<NIOServerCnxn>(sessionlessCnxnTimeout);
    // 关闭过期的连接的线程
    expirerThread = new ConnectionExpirerThread();

    int numCores = Runtime.getRuntime().availableProcessors();
    // 32 cores sweet spot seems to be 4 selector threads
    // selector线程 sqrt(coreSize / 2)
    numSelectorThreads = Integer.getInteger(
        ZOOKEEPER_NIO_NUM_SELECTOR_THREADS,
        Math.max((int) Math.sqrt((float) numCores/2), 1));
    if (numSelectorThreads < 1) {
        throw new IOException("numSelectorThreads must be at least 1");
    }
		// 工作线程coreSize * 2
    numWorkerThreads = Integer.getInteger(
        ZOOKEEPER_NIO_NUM_WORKER_THREADS, 2 * numCores);
    workerShutdownTimeoutMS = Long.getLong(
        ZOOKEEPER_NIO_SHUTDOWN_TIMEOUT, 5000);

    LOG.info("Configuring NIO connection handler with "
             + (sessionlessCnxnTimeout/1000) + "s sessionless connection"
             + " timeout, " + numSelectorThreads + " selector thread(s), "
             + (numWorkerThreads > 0 ? numWorkerThreads : "no")
             + " worker threads, and "
             + (directBufferBytes == 0 ? "gathered writes." :
                ("" + (directBufferBytes/1024) + " kB direct buffers.")));
    for(int i=0; i<numSelectorThreads; ++i) {
        selectorThreads.add(new SelectorThread(i));
    }

    listenBacklog = backlog;
    this.ss = ServerSocketChannel.open();
    ss.socket().setReuseAddress(true);
    LOG.info("binding to port " + addr);
    if (listenBacklog == -1) {
      ss.socket().bind(addr);
    } else {
      ss.socket().bind(addr, listenBacklog);
    }
    ss.configureBlocking(false);
    acceptThread = new AcceptThread(ss, addr, selectorThreads);
}
```



### 用户请求io模型

![image-20200206161342307](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200206161342307.png)

org.apache.zookeeper.server.NIOServerCnxnFactory.AcceptThread#run

```java
public void run() {
    try {
        while (!stopped && !acceptSocket.socket().isClosed()) {
            try {
                select();
            } catch (RuntimeException e) {
                LOG.warn("Ignoring unexpected runtime exception", e);
            } catch (Exception e) {
                LOG.warn("Ignoring unexpected exception", e);
            }
        }
    } finally {
        closeSelector();
        // This will wake up the selector threads, and tell the
        // worker thread pool to begin shutdown.
       if (!reconfiguring) {                    
            NIOServerCnxnFactory.this.stop();
        }
        LOG.info("accept thread exitted run method");
    }
}
```

org.apache.zookeeper.server.NIOServerCnxnFactory.SelectorThread#run

```java
public void run() {
    try {
        while (!stopped) {
            try {
                select();
                processAcceptedConnections();
                processInterestOpsUpdateRequests();
            } catch (RuntimeException e) {
                LOG.warn("Ignoring unexpected runtime exception", e);
            } catch (Exception e) {
                LOG.warn("Ignoring unexpected exception", e);
            }
        }

        // Close connections still pending on the selector. Any others
        // with in-flight work, let drain out of the work queue.
        for (SelectionKey key : selector.keys()) {
            NIOServerCnxn cnxn = (NIOServerCnxn) key.attachment();
            if (cnxn.isSelectable()) {
                cnxn.close();
            }
            cleanupSelectionKey(key);
        }
        SocketChannel accepted;
        while ((accepted = acceptedQueue.poll()) != null) {
            fastCloseSock(accepted);
        }
        updateQueue.clear();
    } finally {
        closeSelector();
        // This will wake up the accept thread and the other selector
        // threads, and tell the worker thread pool to begin shutdown.
        NIOServerCnxnFactory.this.stop();
        LOG.info("selector thread exitted run method");
    }
}
```

org.apache.zookeeper.server.NIOServerCnxnFactory.SelectorThread#select

```java
private void select() {
    try {
        selector.select();

        Set<SelectionKey> selected = selector.selectedKeys();
        ArrayList<SelectionKey> selectedList =
            new ArrayList<SelectionKey>(selected);
        Collections.shuffle(selectedList);
        Iterator<SelectionKey> selectedKeys = selectedList.iterator();
        while(!stopped && selectedKeys.hasNext()) {
            SelectionKey key = selectedKeys.next();
            selected.remove(key);

            if (!key.isValid()) {
                cleanupSelectionKey(key);
                continue;
            }
            if (key.isReadable() || key.isWritable()) {
                handleIO(key);
            } else {
                LOG.warn("Unexpected ops in select " + key.readyOps());
            }
        }
    } catch (IOException e) {
        LOG.warn("Ignoring IOException while selecting", e);
    }
}
```



```java
public void startup(ZooKeeperServer zks, boolean startServer)
        throws IOException, InterruptedException {
    start();
    setZooKeeperServer(zks);
    if (startServer) {
        zks.startdata();
        zks.startup();
    }
}
```

org.apache.zookeeper.server.quorum.QuorumPeer#QuorumPeer()

```java
public QuorumPeer() throws SaslException {
    super("QuorumPeer");
    quorumStats = new QuorumStats(this);
    jmxRemotePeerBean = new HashMap<Long, RemotePeerBean>();
    adminServer = AdminServerFactory.createAdminServer();
    x509Util = createX509Util();
    initialize();
}
```

org.apache.zookeeper.server.quorum.QuorumPeer#start

```java
public synchronized void start() {
    if (!getView().containsKey(myid)) {
        throw new RuntimeException("My id " + myid + " not in the peer list");
     }
    // 加载快照和增量log到内存dataTree
    loadDataBase();
    // 启动io线程
    startServerCnxnFactory();
    try {
        adminServer.start();
    } catch (AdminServerException e) {
        LOG.warn("Problem starting AdminServer", e);
        System.out.println(e);
    }
    // 领导者选举准备工作，创建io线程
    startLeaderElection();
    startJvmPauseMonitor();
    // 开启选举
    super.start();
}
```

```java
private void startServerCnxnFactory() {
    if (cnxnFactory != null) {
      	// 创建workerPool，启动客户端连接io线程selectorThread、acceptThread
        cnxnFactory.start();
    }
    if (secureCnxnFactory != null) {
        secureCnxnFactory.start();
    }
}
```

```java
public void start() {
    stopped = false;
    if (workerPool == null) {
        workerPool = new WorkerService(
            "NIOWorker", numWorkerThreads, false);
    }
    for(SelectorThread thread : selectorThreads) {
        if (thread.getState() == Thread.State.NEW) {
            thread.start();
        }
    }
    // ensure thread is started once and only once
    if (acceptThread.getState() == Thread.State.NEW) {
        acceptThread.start();
    }
    if (expirerThread.getState() == Thread.State.NEW) {
        expirerThread.start();
    }
}
```

### 选举

下面任何一种情况，都会触发 Leader 选举：

1. 启动时，集群服务器刚启动
2. 运行时，Leader 崩溃

zxid最大，serverid最大

准备工作，开启io线程

org.apache.zookeeper.server.quorum.QuorumPeer#startLeaderElection

```java
synchronized public void startLeaderElection() {
    try {
        if (getPeerState() == ServerState.LOOKING) {
          	// 当前投自己
            currentVote = new Vote(myid, getLastLoggedZxid(), getCurrentEpoch());
        }
    } catch(IOException e) {
        RuntimeException re = new RuntimeException(e.getMessage());
        re.setStackTrace(e.getStackTrace());
        throw re;
    }

    this.electionAlg = createElectionAlgorithm(electionType);
}
```

```java
protected Election createElectionAlgorithm(int electionAlgorithm){
    Election le=null;

    //TODO: use a factory rather than a switch
    switch (electionAlgorithm) {
    case 1:
        le = new AuthFastLeaderElection(this);
        break;
    case 2:
        le = new AuthFastLeaderElection(this, true);
        break;
    case 3:
        // 默认用FastLeaderElection
        QuorumCnxManager qcm = createCnxnManager();
        QuorumCnxManager oldQcm = qcmRef.getAndSet(qcm);
        if (oldQcm != null) {
            LOG.warn("Clobbering already-set QuorumCnxManager (restarting leader election?)");
            oldQcm.halt();
        }
        QuorumCnxManager.Listener listener = qcm.listener;
        if(listener != null){
            listener.start();
            FastLeaderElection fle = new FastLeaderElection(this, qcm);
            fle.start();
            le = fle;
        } else {
            LOG.error("Null listener when initializing cnx manager");
        }
        break;
    default:
        assert false;
    }
    return le;
}
```

开启选举和集群通信，线程一直运行while (running)

```java
super.start()
```

org.apache.zookeeper.server.quorum.QuorumPeer#run

```java
public void run() {
    updateThreadName();

    LOG.debug("Starting quorum peer");
    try {
        jmxQuorumBean = new QuorumBean(this);
        MBeanRegistry.getInstance().register(jmxQuorumBean, null);
        for(QuorumServer s: getView().values()){
          	// 遍历所有server
            ZKMBeanInfo p;
            if (getId() == s.id) {
                p = jmxLocalPeerBean = new LocalPeerBean(this);
                try {
                    MBeanRegistry.getInstance().register(p, jmxQuorumBean);
                } catch (Exception e) {
                    LOG.warn("Failed to register with JMX", e);
                    jmxLocalPeerBean = null;
                }
            } else {
                RemotePeerBean rBean = new RemotePeerBean(this, s);
                try {
                    MBeanRegistry.getInstance().register(rBean, jmxQuorumBean);
                    jmxRemotePeerBean.put(s.id, rBean);
                } catch (Exception e) {
                    LOG.warn("Failed to register with JMX", e);
                }
            }
        }
    } catch (Exception e) {
        LOG.warn("Failed to register with JMX", e);
        jmxQuorumBean = null;
    }

    try {
        /*
         * Main loop
         */
        while (running) {
            switch (getPeerState()) {
            case LOOKING:
                LOG.info("LOOKING");
                ServerMetrics.getMetrics().LOOKING_COUNT.add(1);

                if (Boolean.getBoolean("readonlymode.enabled")) {
                    LOG.info("Attempting to start ReadOnlyZooKeeperServer");

                    // Create read-only server but don't start it immediately
                    final ReadOnlyZooKeeperServer roZk =
                        new ReadOnlyZooKeeperServer(logFactory, this, this.zkDb);

                    // Instead of starting roZk immediately, wait some grace
                    // period before we decide we're partitioned.
                    //
                    // Thread is used here because otherwise it would require
                    // changes in each of election strategy classes which is
                    // unnecessary code coupling.
                    Thread roZkMgr = new Thread() {
                        public void run() {
                            try {
                                // lower-bound grace period to 2 secs
                                sleep(Math.max(2000, tickTime));
                                if (ServerState.LOOKING.equals(getPeerState())) {
                                    roZk.startup();
                                }
                            } catch (InterruptedException e) {
                                LOG.info("Interrupted while attempting to start ReadOnlyZooKeeperServer, not started");
                            } catch (Exception e) {
                                LOG.error("FAILED to start ReadOnlyZooKeeperServer", e);
                            }
                        }
                    };
                    try {
                        roZkMgr.start();
                        reconfigFlagClear();
                        if (shuttingDownLE) {
                            shuttingDownLE = false;
                            startLeaderElection();
                        }
                      	// 开始选举
                        setCurrentVote(makeLEStrategy().lookForLeader());
                    } catch (Exception e) {
                        LOG.warn("Unexpected exception", e);
                        setPeerState(ServerState.LOOKING);
                    } finally {
                        // If the thread is in the the grace period, interrupt
                        // to come out of waiting.
                        roZkMgr.interrupt();
                        roZk.shutdown();
                    }
                } else {
                    try {
                       reconfigFlagClear();
                        if (shuttingDownLE) {
                           shuttingDownLE = false;
                           startLeaderElection();
                           }
                        // 开始选举
                        setCurrentVote(makeLEStrategy().lookForLeader());
                    } catch (Exception e) {
                        LOG.warn("Unexpected exception", e);
                        setPeerState(ServerState.LOOKING);
                    }                        
                }
                break;
            case OBSERVING:
                try {
                    LOG.info("OBSERVING");
                    setObserver(makeObserver(logFactory));
                    observer.observeLeader();
                } catch (Exception e) {
                    LOG.warn("Unexpected exception",e );
                } finally {
                    observer.shutdown();
                    setObserver(null);
                    updateServerState();

                    // Add delay jitter before we switch to LOOKING
                    // state to reduce the load of ObserverMaster
                    if (isRunning()) {
                        Observer.waitForObserverElectionDelay();
                    }
                }
                break;
            case FOLLOWING:
                try {
                   LOG.info("FOLLOWING");
                    setFollower(makeFollower(logFactory));
                    follower.followLeader();
                } catch (Exception e) {
                   LOG.warn("Unexpected exception",e);
                } finally {
                   follower.shutdown();
                   setFollower(null);
                   updateServerState();
                }
                break;
            case LEADING:
                // 当前是leading角色
                LOG.info("LEADING");
                try {
                    setLeader(makeLeader(logFactory));
                    leader.lead();
                    setLeader(null);
                } catch (Exception e) {
                    LOG.warn("Unexpected exception",e);
                } finally {
                    if (leader != null) {
                        leader.shutdown("Forcing shutdown");
                        setLeader(null);
                    }
                    updateServerState();
                }
                break;
            }
            start_fle = Time.currentElapsedTime();
        }
    } finally {
        LOG.warn("QuorumPeer main thread exited");
        MBeanRegistry instance = MBeanRegistry.getInstance();
        instance.unregister(jmxQuorumBean);
        instance.unregister(jmxLocalPeerBean);

        for (RemotePeerBean remotePeerBean : jmxRemotePeerBean.values()) {
            instance.unregister(remotePeerBean);
        }

        jmxQuorumBean = null;
        jmxLocalPeerBean = null;
        jmxRemotePeerBean = null;
    }
}
```

当当前服务的状态是LOOKING，则开启新一轮选举

**选举开始**

org.apache.zookeeper.server.quorum.FastLeaderElection#lookForLeader

```java
public Vote lookForLeader() throws InterruptedException {
    try {
        self.jmxLeaderElectionBean = new LeaderElectionBean();
        MBeanRegistry.getInstance().register(
                self.jmxLeaderElectionBean, self.jmxLocalPeerBean);
    } catch (Exception e) {
        LOG.warn("Failed to register with JMX", e);
        self.jmxLeaderElectionBean = null;
    }
    if (self.start_fle == 0) {
       self.start_fle = Time.currentElapsedTime();
    }
    try {
        Map<Long, Vote> recvset = new HashMap<Long, Vote>();

        Map<Long, Vote> outofelection = new HashMap<Long, Vote>();

        int notTimeout = minNotificationInterval;

        synchronized(this){
            logicalclock.incrementAndGet();
            // 启动的时候首先把票投给自己
            updateProposal(getInitId(), getInitLastLoggedZxid(), getPeerEpoch());
        }

        LOG.info("New election. My id =  " + self.getId() +
                ", proposed zxid=0x" + Long.toHexString(proposedZxid));
      	// 发送选举自己的广播通知
        sendNotifications();

        SyncedLearnerTracker voteSet;

        /*
         * Loop in which we exchange notifications until we find a leader
         */

        while ((self.getPeerState() == ServerState.LOOKING) &&
                (!stop)){
            /*
             * Remove next notification from queue, times out after 2 times
             * the termination time
             */
          	// 接收选举通知，投自己票也能从recvqueue里拿到
          	/*
          	启动时候，自己的投票结构
          	version = 1
            leader = 1
            zxid = 0
            electionEpoch = 1
            state = {QuorumPeer$ServerState@1386} "LOOKING"
            sid = 1
            peerEpoch = 0
          	*/
            Notification n = recvqueue.poll(notTimeout,
                    TimeUnit.MILLISECONDS);

            /*
             * Sends more notifications if haven't received enough.
             * Otherwise processes new notification.
             */
            if(n == null){
                if(manager.haveDelivered()){
                  	// queueSendMap空
                    sendNotifications();
                } else {
                  	// 队列里还有数据没发送，认为还未连接成功，重新连接
                    manager.connectAll();
                }

                /*
                 * Exponential backoff
                 */
                int tmpTimeOut = notTimeout*2;
                notTimeout = (tmpTimeOut < maxNotificationInterval?
                        tmpTimeOut : maxNotificationInterval);
                LOG.info("Notification time out: " + notTimeout);
            }
            else if (validVoter(n.sid) && validVoter(n.leader)) {
              	// sid和leader都在服务器列表中
                /*
                 * Only proceed if the vote comes from a replica in the current or next
                 * voting view for a replica in the current or next voting view.
                 */
                switch (n.state) {
                case LOOKING:
                    if (getInitLastLoggedZxid() == -1) {
                        LOG.debug("Ignoring notification as our zxid is -1");
                        break;
                    }
                    if (n.zxid == -1) {
                        LOG.debug("Ignoring notification from member with -1 zxid" + n.sid);
                        break;
                    }
                    // If notification > current, replace and send messages out
                    if (n.electionEpoch > logicalclock.get()) {
                      	// 对方的投票届数大于自己的
                        logicalclock.set(n.electionEpoch);
                        recvset.clear();
                        if(totalOrderPredicate(n.leader, n.zxid, n.peerEpoch,
                                getInitId(), getInitLastLoggedZxid(), getPeerEpoch())) {
                          	// 对方胜利，更新自己的选票，和对方的投票一致
                            updateProposal(n.leader, n.zxid, n.peerEpoch);
                        } else {
                          	// 否则，更新自己的投票
                            updateProposal(getInitId(),
                                    getInitLastLoggedZxid(),
                                    getPeerEpoch());
                        }
                      	// 发送投票结果
                        sendNotifications();
                    } else if (n.electionEpoch < logicalclock.get()) {
                      	// 对方的投票届数小于自己，丢弃
                        if(LOG.isDebugEnabled()){
                            LOG.debug("Notification election epoch is smaller than logicalclock. n.electionEpoch = 0x"
                                    + Long.toHexString(n.electionEpoch)
                                    + ", logicalclock=0x" + Long.toHexString(logicalclock.get()));
                        }
                        break;
                    } else if (totalOrderPredicate(n.leader, n.zxid, n.peerEpoch,
                            proposedLeader, proposedZxid, proposedEpoch)) {
                        updateProposal(n.leader, n.zxid, n.peerEpoch);
                        sendNotifications();
                    }

                    if(LOG.isDebugEnabled()){
                        LOG.debug("Adding vote: from=" + n.sid +
                                ", proposed leader=" + n.leader +
                                ", proposed zxid=0x" + Long.toHexString(n.zxid) +
                                ", proposed election epoch=0x" + Long.toHexString(n.electionEpoch));
                    }

                    // don't care about the version if it's in LOOKING state
                    // 保存sid的投票
                    recvset.put(n.sid, new Vote(n.leader, n.zxid, n.electionEpoch, n.peerEpoch));

                    voteSet = getVoteTracker(
                            recvset, new Vote(proposedLeader, proposedZxid,
                                    logicalclock.get(), proposedEpoch));

                    // 判断，自己的投票在所有投票结果中是否过半
                    if (voteSet.hasAllQuorums()) {
                        // Verify if there is any change in the proposed leader
                      	// 已经选出leader，recvqueue里还有投票数据，继续比较谁胜利
                        while((n = recvqueue.poll(finalizeWait,
                                TimeUnit.MILLISECONDS)) != null){
                            if(totalOrderPredicate(n.leader, n.zxid, n.peerEpoch,
                                    proposedLeader, proposedZxid, proposedEpoch)){
                                recvqueue.put(n);
                                break;
                            }
                        }

                        /*
                         * This predicate is true once we don't read any new
                         * relevant message from the reception queue
                         */
                        if (n == null) {
                          	// 最终选出了leader
                          	// 设置自己的角色
                            setPeerState(proposedLeader, voteSet);
                          	
                            Vote endVote = new Vote(proposedLeader,
                                    proposedZxid, logicalclock.get(), 
                                    proposedEpoch);
                          	// 清空recvqueue队列
                            leaveInstance(endVote);
                            return endVote;
                        }
                    }
                    break;
                case OBSERVING:
                    LOG.debug("Notification from observer: " + n.sid);
                    break;
                case FOLLOWING:
                case LEADING:
                    /*
                     * Consider all notifications from the same epoch
                     * together.
                     */
                    if(n.electionEpoch == logicalclock.get()){
                        recvset.put(n.sid, new Vote(n.leader, n.zxid, n.electionEpoch, n.peerEpoch));
                        voteSet = getVoteTracker(recvset, new Vote(n.version, 
                                  n.leader, n.zxid, n.electionEpoch, n.peerEpoch, n.state));
                        if (voteSet.hasAllQuorums() && 
                                checkLeader(outofelection, n.leader, n.electionEpoch)) {
                            setPeerState(n.leader, voteSet);
                            Vote endVote = new Vote(n.leader, 
                                    n.zxid, n.electionEpoch, n.peerEpoch);
                            leaveInstance(endVote);
                            return endVote;
                        }
                    }

                    /*
                     * Before joining an established ensemble, verify that
                     * a majority are following the same leader.
                     */
                    outofelection.put(n.sid, new Vote(n.version, n.leader,
                            n.zxid, n.electionEpoch, n.peerEpoch, n.state));
                    voteSet = getVoteTracker(outofelection, new Vote(n.version, 
                            n.leader, n.zxid, n.electionEpoch, n.peerEpoch, n.state));

                    if (voteSet.hasAllQuorums() &&
                            checkLeader(outofelection, n.leader, n.electionEpoch)) {
                        synchronized(this){
                            logicalclock.set(n.electionEpoch);
                            setPeerState(n.leader, voteSet);
                        }
                        Vote endVote = new Vote(n.leader, n.zxid, 
                                n.electionEpoch, n.peerEpoch);
                        leaveInstance(endVote);
                        return endVote;
                    }
                    break;
                default:
                    LOG.warn("Notification state unrecoginized: " + n.state
                          + " (n.state), " + n.sid + " (n.sid)");
                    break;
                }
            } else {
                if (!validVoter(n.leader)) {
                    LOG.warn("Ignoring notification for non-cluster member sid {} from sid {}", n.leader, n.sid);
                }
                if (!validVoter(n.sid)) {
                    LOG.warn("Ignoring notification for sid {} from non-quorum member sid {}", n.leader, n.sid);
                }
            }
        }
        return null;
    } finally {
        try {
            if(self.jmxLeaderElectionBean != null){
                MBeanRegistry.getInstance().unregister(
                        self.jmxLeaderElectionBean);
            }
        } catch (Exception e) {
            LOG.warn("Failed to unregister with JMX", e);
        }
        self.jmxLeaderElectionBean = null;
        LOG.debug("Number of connection processing threads: {}",
                manager.getConnectionThreadCount());
    }
}
```

```java
private void sendNotifications() {
    for (long sid : self.getCurrentAndNextConfigVoters()) {
      	// 遍历所有serverid
        QuorumVerifier qv = self.getQuorumVerifier();
        ToSend notmsg = new ToSend(ToSend.mType.notification,
                proposedLeader,
                proposedZxid,
                logicalclock.get(),
                QuorumPeer.ServerState.LOOKING,
                sid,
                proposedEpoch, qv.toString().getBytes());
        if(LOG.isDebugEnabled()){
            LOG.debug("Sending Notification: " + proposedLeader + " (n.leader), 0x"  +
                  Long.toHexString(proposedZxid) + " (n.zxid), 0x" + Long.toHexString(logicalclock.get())  +
                  " (n.round), " + sid + " (recipient), " + self.getId() +
                  " (myid), 0x" + Long.toHexString(proposedEpoch) + " (n.peerEpoch)");
        }
        sendqueue.offer(notmsg);
    }
}
```

org.apache.zookeeper.server.quorum.FastLeaderElection#totalOrderPredicate

```java
protected boolean totalOrderPredicate(long newId, long newZxid, long newEpoch, long curId, long curZxid, long curEpoch) {
    LOG.debug("id: " + newId + ", proposed id: " + curId + ", zxid: 0x" +
            Long.toHexString(newZxid) + ", proposed zxid: 0x" + Long.toHexString(curZxid));
    if(self.getQuorumVerifier().getWeight(newId) == 0){
        return false;
    }
    
    /*
     * We return true if one of the following three cases hold:
     * 1- New epoch is higher
     * 2- New epoch is the same as current epoch, but new zxid is higher
     * 3- New epoch is the same as current epoch, new zxid is the same
     *  as current zxid, but server id is higher.
     */
    // epoch -> zxid -> serverid
    return ((newEpoch > curEpoch) || 
            ((newEpoch == curEpoch) &&
            ((newZxid > curZxid) || ((newZxid == curZxid) && (newId > curId)))));
}
```

```java
protected boolean termPredicate(
        HashMap<Long, Vote> votes,
        Vote vote) {

    HashSet<Long> set = new HashSet<Long>();

    /*
     * First make the views consistent. Sometimes peers will have
     * different zxids for a server depending on timing.
     */
  	// 选择和自己投票一样的票
    for (Map.Entry<Long,Vote> entry : votes.entrySet()) {
        if (vote.equals(entry.getValue())){
            set.add(entry.getKey());
        }
    }
	
 		// 超过一半返回true
    return self.getQuorumVerifier().containsQuorum(set);
}
```

org.apache.zookeeper.server.quorum.flexible.QuorumMaj#containsQuorum

```java
public boolean containsQuorum(Set<Long> set){
    return (set.size() > half);
}
```

主要逻辑：

接受其他服务器的投票，和自己的投票结果做比较，选择最强大的投票结果，并更新自己的投票，最后统计和自己的投票结果一样的票数是否超过一半，超过则选出了leader，没有则继续

![image-20200310084906400](/Users/daitechang/Documents/hexo_blog/source/_posts/pic/image-20200310084906400.png)

### IO模型

AcceptThread

SelectorThread

workerThread

## 处理请求

org.apache.zookeeper.server.NIOServerCnxnFactory.IOWorkRequest#doWork

```java
public void doWork() throws InterruptedException {
    if (!key.isValid()) {
        selectorThread.cleanupSelectionKey(key);
        return;
    }

    if (key.isReadable() || key.isWritable()) {
        cnxn.doIO(key);

        // Check if we shutdown or doIO() closed this connection
        if (stopped) {
            cnxn.close();
            return;
        }
        if (!key.isValid()) {
            selectorThread.cleanupSelectionKey(key);
            return;
        }
        touchCnxn(cnxn);
    }

    // Mark this connection as once again ready for selection
    cnxn.enableSelectable();
    // Push an update request on the queue to resume selecting
    // on the current set of interest ops, which may have changed
    // as a result of the I/O operations we just performed.
    if (!selectorThread.addInterestOpsUpdateRequest(key)) {
        cnxn.close();
    }
}
```

```java
void doIO(SelectionKey k) throws InterruptedException {
    try {
        if (isSocketOpen() == false) {
            LOG.warn("trying to do i/o on a null socket for session:0x"
                     + Long.toHexString(sessionId));

            return;
        }
        if (k.isReadable()) {
            int rc = sock.read(incomingBuffer);
            if (rc < 0) {
                ServerMetrics.getMetrics().CONNECTION_DROP_COUNT.add(1);
                throw new EndOfStreamException(
                        "Unable to read additional data from client sessionid 0x"
                        + Long.toHexString(sessionId)
                        + ", likely client has closed socket");
            }
            if (incomingBuffer.remaining() == 0) {
                boolean isPayload;
                if (incomingBuffer == lenBuffer) { // start of next request
                    incomingBuffer.flip();
                    isPayload = readLength(k);
                    incomingBuffer.clear();
                } else {
                    // continuation
                    isPayload = true;
                }
                if (isPayload) { // not the case for 4letterword
                    readPayload();
                }
                else {
                    // four letter words take care
                    // need not do anything else
                    return;
                }
            }
        }
        if (k.isWritable()) {
            handleWrite(k);

            if (!initialized && !getReadInterest() && !getWriteInterest()) {
                throw new CloseRequestException("responded to info probe");
            }
        }
    } catch (CancelledKeyException e) {
        ...
    }
}
```

org.apache.zookeeper.server.NIOServerCnxn#readPayload

org.apache.zookeeper.server.NIOServerCnxn#readRequest

org.apache.zookeeper.server.ZooKeeperServer#processPacket

```java
public void processPacket(ServerCnxn cnxn, ByteBuffer incomingBuffer) throws IOException {
    // We have the request, now process and setup for next
    InputStream bais = new ByteBufferInputStream(incomingBuffer);
    BinaryInputArchive bia = BinaryInputArchive.getArchive(bais);
    RequestHeader h = new RequestHeader();
    h.deserialize(bia, "header");

    // Need to increase the outstanding request count first, otherwise
    // there might be a race condition that it enabled recv after
    // processing request and then disabled when check throttling.
    //
    // Be aware that we're actually checking the global outstanding
    // request before this request.
    //
    // It's fine if the IOException thrown before we decrease the count
    // in cnxn, since it will close the cnxn anyway.
    cnxn.incrOutstandingAndCheckThrottle(h);

    // Through the magic of byte buffers, txn will not be
    // pointing
    // to the start of the txn
    incomingBuffer = incomingBuffer.slice();
    if (h.getType() == OpCode.auth) {
        LOG.info("got auth packet " + cnxn.getRemoteSocketAddress());
        AuthPacket authPacket = new AuthPacket();
        ByteBufferInputStream.byteBuffer2Record(incomingBuffer, authPacket);
        String scheme = authPacket.getScheme();
        ServerAuthenticationProvider ap = ProviderRegistry.getServerProvider(scheme);
        Code authReturn = KeeperException.Code.AUTHFAILED;
        if(ap != null) {
            try {
                // handleAuthentication may close the connection, to allow the client to choose
                // a different server to connect to.
                authReturn = ap.handleAuthentication(new ServerAuthenticationProvider.ServerObjs(this, cnxn), authPacket.getAuth());
            } catch(RuntimeException e) {
                LOG.warn("Caught runtime exception from AuthenticationProvider: " + scheme + " due to " + e);
                authReturn = KeeperException.Code.AUTHFAILED;
            }
        }
        if (authReturn == KeeperException.Code.OK) {
            if (LOG.isDebugEnabled()) {
                LOG.debug("Authentication succeeded for scheme: " + scheme);
            }
            LOG.info("auth success " + cnxn.getRemoteSocketAddress());
            ReplyHeader rh = new ReplyHeader(h.getXid(), 0,
                    KeeperException.Code.OK.intValue());
            cnxn.sendResponse(rh, null, null);
        } else {
            if (ap == null) {
                LOG.warn("No authentication provider for scheme: "
                        + scheme + " has "
                        + ProviderRegistry.listProviders());
            } else {
                LOG.warn("Authentication failed for scheme: " + scheme);
            }
            // send a response...
            ReplyHeader rh = new ReplyHeader(h.getXid(), 0,
                    KeeperException.Code.AUTHFAILED.intValue());
            cnxn.sendResponse(rh, null, null);
            // ... and close connection
            cnxn.sendBuffer(ServerCnxnFactory.closeConn);
            cnxn.disableRecv();
        }
        return;
    } else if (h.getType() == OpCode.sasl) {
        Record rsp = processSasl(incomingBuffer,cnxn);
        ReplyHeader rh = new ReplyHeader(h.getXid(), 0, KeeperException.Code.OK.intValue());
        cnxn.sendResponse(rh,rsp, "response"); // not sure about 3rd arg..what is it?
        return;
    } else {
        Request si = new Request(cnxn, cnxn.getSessionId(), h.getXid(),
          h.getType(), incomingBuffer, cnxn.getAuthInfo());
        si.setOwner(ServerCnxn.me);
        // Always treat packet from the client as a possible
        // local request.
        setLocalSessionFlag(si);
      	// 提交请求
        submitRequest(si);
        return;
    }
}
```

链式处理请求

以commitProcessor为例

```java
public CommitProcessor(RequestProcessor nextProcessor, String id,
                       boolean matchSyncs, ZooKeeperServerListener listener) {
    super("CommitProcessor:" + id, listener);
    this.nextProcessor = nextProcessor;
    this.matchSyncs = matchSyncs;
}
```

org.apache.zookeeper.server.ZooKeeperServer#submitRequest

```java
public void submitRequest(Request si) {
    if (firstProcessor == null) {
        synchronized (this) {
            try {
                // Since all requests are passed to the request
                // processor it should wait for setting up the request
                // processor chain. The state will be updated to RUNNING
                // after the setup.
                while (state == State.INITIAL) {
                    wait(1000);
                }
            } catch (InterruptedException e) {
                LOG.warn("Unexpected interruption", e);
            }
            if (firstProcessor == null || state != State.RUNNING) {
                throw new RuntimeException("Not started");
            }
        }
    }
    try {
        touch(si.cnxn);
        boolean validpacket = Request.isValid(si.type);
        if (validpacket) {
            firstProcessor.processRequest(si);
            if (si.cnxn != null) {
                incInProcess();
            }
        } else {
            LOG.warn("Received packet at server of unknown type " + si.type);
            new UnimplementedRequestProcessor().processRequest(si);
        }
    } catch (MissingSessionException e) {
     ...
    }
}
```

```java
public interface RequestProcessor {
    @SuppressWarnings("serial")
    public static class RequestProcessorException extends Exception {
        public RequestProcessorException(String msg, Throwable t) {
            super(msg, t);
        }
    }

    void processRequest(Request request) throws RequestProcessorException;

    void shutdown();
}
```

􏱐􏳀􏳁􏳂􏰪单机模式：

每个处理器是个单线程，不会有竞争出现

1. firstProcessor = PrepRequestProcessor(􏲣􏰎)
2. PrepRequestProcessor.next = SyncRequestProcessor(􏲣􏰎) 
3. SyncRequestProcessor.next FinalRequestProcessor



org.apache.zookeeper.server.PrepRequestProcessor#processRequest

```java
public void processRequest(Request request) {
    request.prepQueueStartTime =  Time.currentElapsedTime();
  	// 提交到submittedRequests队列
    submittedRequests.add(request);
    ServerMetrics.getMetrics().PREP_PROCESSOR_QUEUED.add(1);
}
```

org.apache.zookeeper.server.PrepRequestProcessor#pRequest

```java
protected void pRequest(Request request) throws RequestProcessorException {
    // LOG.info("Prep>>> cxid = " + request.cxid + " type = " +
    // request.type + " id = 0x" + Long.toHexString(request.sessionId));
    request.setHdr(null);
    request.setTxn(null);

    try {
        switch (request.type) {
        case OpCode.createContainer:
        case OpCode.create:
        case OpCode.create2:
            CreateRequest create2Request = new CreateRequest();
            pRequest2Txn(request.type, zks.getNextZxid(), request, create2Request, true);
            break;
        case OpCode.createTTL:
            CreateTTLRequest createTtlRequest = new CreateTTLRequest();
            pRequest2Txn(request.type, zks.getNextZxid(), request, createTtlRequest, true);
            break;
        case OpCode.deleteContainer:
        case OpCode.delete:
            DeleteRequest deleteRequest = new DeleteRequest();
            pRequest2Txn(request.type, zks.getNextZxid(), request, deleteRequest, true);
            break;
        case OpCode.setData:
            SetDataRequest setDataRequest = new SetDataRequest();
            pRequest2Txn(request.type, zks.getNextZxid(), request, setDataRequest, true);
            break;
        case OpCode.reconfig:
            ReconfigRequest reconfigRequest = new ReconfigRequest();
            ByteBufferInputStream.byteBuffer2Record(request.request, reconfigRequest);
            pRequest2Txn(request.type, zks.getNextZxid(), request, reconfigRequest, true);
            break;
        case OpCode.setACL:
            SetACLRequest setAclRequest = new SetACLRequest();
            pRequest2Txn(request.type, zks.getNextZxid(), request, setAclRequest, true);
            break;
        case OpCode.check:
            CheckVersionRequest checkRequest = new CheckVersionRequest();
            pRequest2Txn(request.type, zks.getNextZxid(), request, checkRequest, true);
            break;
        case OpCode.multi:
            MultiTransactionRecord multiRequest = new MultiTransactionRecord();
            try {
                ByteBufferInputStream.byteBuffer2Record(request.request, multiRequest);
            } catch(IOException e) {
                request.setHdr(new TxnHeader(request.sessionId, request.cxid, zks.getNextZxid(),
                        Time.currentWallTime(), OpCode.multi));
                throw e;
            }
            List<Txn> txns = new ArrayList<Txn>();
            //Each op in a multi-op must have the same zxid!
            long zxid = zks.getNextZxid();
            KeeperException ke = null;

            //Store off current pending change records in case we need to rollback
            Map<String, ChangeRecord> pendingChanges = getPendingChanges(multiRequest);

            for(Op op: multiRequest) {
                Record subrequest = op.toRequestRecord();
                int type;
                Record txn;

                /* If we've already failed one of the ops, don't bother
                 * trying the rest as we know it's going to fail and it
                 * would be confusing in the logfiles.
                 */
                if (ke != null) {
                    type = OpCode.error;
                    txn = new ErrorTxn(Code.RUNTIMEINCONSISTENCY.intValue());
                }

                /* Prep the request and convert to a Txn */
                else {
                    try {
                        pRequest2Txn(op.getType(), zxid, request, subrequest, false);
                        type = request.getHdr().getType();
                        txn = request.getTxn();
                    } catch (KeeperException e) {
                        ke = e;
                        type = OpCode.error;
                        txn = new ErrorTxn(e.code().intValue());

                        if (e.code().intValue() > Code.APIERROR.intValue()) {
                            LOG.info("Got user-level KeeperException when processing {} aborting" +
                                    " remaining multi ops. Error Path:{} Error:{}",
                                    request.toString(), e.getPath(), e.getMessage());
                        }

                        request.setException(e);

                        /* Rollback change records from failed multi-op */
                        rollbackPendingChanges(zxid, pendingChanges);
                    }
                }

                //FIXME: I don't want to have to serialize it here and then
                //       immediately deserialize in next processor. But I'm
                //       not sure how else to get the txn stored into our list.
                try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
                    BinaryOutputArchive boa = BinaryOutputArchive.getArchive(baos);
                    txn.serialize(boa, "request");
                    ByteBuffer bb = ByteBuffer.wrap(baos.toByteArray());
                    txns.add(new Txn(type, bb.array()));
                }
            }

            request.setHdr(new TxnHeader(request.sessionId, request.cxid, zxid,
                    Time.currentWallTime(), request.type));
            request.setTxn(new MultiTxn(txns));

            break;

        //create/close session don't require request record
        case OpCode.createSession:
        case OpCode.closeSession:
            if (!request.isLocalSession()) {
                pRequest2Txn(request.type, zks.getNextZxid(), request,
                             null, true);
            }
            break;

        //All the rest don't need to create a Txn - just verify session
        case OpCode.sync:
        case OpCode.exists:
        case OpCode.getData:
        case OpCode.getACL:
        case OpCode.getChildren:
        case OpCode.getAllChildrenNumber:
        case OpCode.getChildren2:
        case OpCode.ping:
        case OpCode.setWatches:
        case OpCode.checkWatches:
        case OpCode.removeWatches:
        case OpCode.getEphemerals:
            zks.sessionTracker.checkSession(request.sessionId,
                    request.getOwner());
            break;
        default:
            LOG.warn("unknown type " + request.type);
            break;
        }
    } catch (KeeperException e) {
        if (request.getHdr() != null) {
            request.getHdr().setType(OpCode.error);
            request.setTxn(new ErrorTxn(e.code().intValue()));
        }

        if (e.code().intValue() > Code.APIERROR.intValue()) {
            LOG.info("Got user-level KeeperException when processing {} Error Path:{} Error:{}",
                    request.toString(), e.getPath(), e.getMessage());
        }
        request.setException(e);
    } catch (Exception e) {
        // log at error level as we are returning a marshalling
        // error to the user
        LOG.error("Failed to process " + request, e);

        StringBuilder sb = new StringBuilder();
        ByteBuffer bb = request.request;
        if(bb != null){
            bb.rewind();
            while (bb.hasRemaining()) {
                sb.append(Integer.toHexString(bb.get() & 0xff));
            }
        } else {
            sb.append("request buffer is null");
        }

        LOG.error("Dumping request buffer: 0x" + sb.toString());
        if (request.getHdr() != null) {
            request.getHdr().setType(OpCode.error);
            request.setTxn(new ErrorTxn(Code.MARSHALLINGERROR.intValue()));
        }
    }
    request.zxid = zks.getZxid();
    ServerMetrics.getMetrics().PREP_PROCESS_TIME.add(Time.currentElapsedTime() - request.prepStartTime);
    nextProcessor.processRequest(request);
}
```

1. 创建事务日志
2. 快照，database，文件
3. 更新内存，dataTree
4. 返回结果



## 客户端

使用nio连接服务器

开启两个线程
sendThread

eventThread

org.apache.zookeeper.ZooKeeper#ZooKeeper(java.lang.String, int, org.apache.zookeeper.Watcher, boolean, org.apache.zookeeper.client.HostProvider, org.apache.zookeeper.client.ZKClientConfig)

```java
public ZooKeeper(String connectString, int sessionTimeout, Watcher watcher,
        boolean canBeReadOnly, HostProvider aHostProvider,
        ZKClientConfig clientConfig) throws IOException {
    LOG.info("Initiating client connection, connectString=" + connectString
            + " sessionTimeout=" + sessionTimeout + " watcher=" + watcher);

    if (clientConfig == null) {
        clientConfig = new ZKClientConfig();
    }
    this.clientConfig = clientConfig;
    watchManager = defaultWatchManager();
    watchManager.defaultWatcher = watcher;
    ConnectStringParser connectStringParser = new ConnectStringParser(
            connectString);
    hostProvider = aHostProvider;

  	// 创建sendThread，eventThread
    cnxn = createConnection(connectStringParser.getChrootPath(),
            hostProvider, sessionTimeout, this, watchManager,
            getClientCnxnSocket(), canBeReadOnly);
    // 开启线程
    cnxn.start();
}
```

```java
public ClientCnxn(String chrootPath, HostProvider hostProvider, int sessionTimeout, ZooKeeper zooKeeper,
        ClientWatchManager watcher, ClientCnxnSocket clientCnxnSocket,
        long sessionId, byte[] sessionPasswd, boolean canBeReadOnly) {
    this.zooKeeper = zooKeeper;
    this.watcher = watcher;
    this.sessionId = sessionId;
    this.sessionPasswd = sessionPasswd;
    this.sessionTimeout = sessionTimeout;
    this.hostProvider = hostProvider;
    this.chrootPath = chrootPath;

    connectTimeout = sessionTimeout / hostProvider.size();
    readTimeout = sessionTimeout * 2 / 3;
    readOnly = canBeReadOnly;

    sendThread = new SendThread(clientCnxnSocket);
    eventThread = new EventThread();
    this.clientConfig=zooKeeper.getClientConfig();
    initRequestTimeout();
}
```



客户端输入create等命令，zookeeper将命令放入outgoingQueue，sender线程不断从outgoingQueue里取命令，并发送socket给服务端，然后将socket放入pendingqueue里，等待请求返回；同时该线程还回取pendingqueue里的响应

## 数据结构

树形结构，和文件系统的目录结构相似

DataTree

## 角色

leader 读、写、选举

follower 读、选举

observer 读

## 事件监听器

允许用户在指定节点上注册一些watcher

## 消息广播

leader为follower服务器各自分配一个单独的队列，然后将需要广播的事务proposal依次放入队列中，并且根据fifo策略进行消息发送。

每个follower服务器在接收到这个事务之后，首先将其以事务日志的形式写入本地磁盘，成功写入之后发反馈给leader服务器一个ack响应。

当leader服务器收到超过半数follower的ack之后，广播一个commit消息给所有follower，同时自身也会完成事务提交。

follower收到commit之后，完成事务提交

## 崩溃恢复

## 选举策略

zxid事务id最大

zxid相等，则选serverid最大

## Leading

```java
case LEADING:
    LOG.info("LEADING");
    try {
        setLeader(makeLeader(logFactory));
        leader.lead();
        setLeader(null);
    } catch (Exception e) {
        LOG.warn("Unexpected exception",e);
    } finally {
        if (leader != null) {
            leader.shutdown("Forcing shutdown");
            setLeader(null);
        }
        setPeerState(ServerState.LOOKING);
    }
    break;
```

```java
void lead() throws IOException, InterruptedException {
    self.end_fle = Time.currentElapsedTime();
    long electionTimeTaken = self.end_fle - self.start_fle;
    self.setElectionTimeTaken(electionTimeTaken);
    LOG.info("LEADING - LEADER ELECTION TOOK - {}", electionTimeTaken);
    self.start_fle = 0;
    self.end_fle = 0;

    zk.registerJMX(new LeaderBean(this, zk), self.jmxLocalPeerBean);

    try {
        self.tick.set(0);
        zk.loadData();
        
        leaderStateSummary = new StateSummary(self.getCurrentEpoch(), zk.getLastProcessedZxid());

        // Start thread that waits for connection requests from 
        // new followers.
      	// 创建监听线程，监听folowers对他的连接
        cnxAcceptor = new LearnerCnxAcceptor();
        cnxAcceptor.start();
        
        readyToStart = true;
        long epoch = getEpochToPropose(self.getId(), self.getAcceptedEpoch());
        
        zk.setZxid(ZxidUtils.makeZxid(epoch, 0));
        
        synchronized(this){
            lastProposed = zk.getZxid();
        }
        
        newLeaderProposal.packet = new QuorumPacket(NEWLEADER, zk.getZxid(),
                null, null);


        if ((newLeaderProposal.packet.getZxid() & 0xffffffffL) != 0) {
            LOG.info("NEWLEADER proposal has Zxid of "
                    + Long.toHexString(newLeaderProposal.packet.getZxid()));
        }
        
        waitForEpochAck(self.getId(), leaderStateSummary);
        self.setCurrentEpoch(epoch);

        // We have to get at least a majority of servers in sync with
        // us. We do this by waiting for the NEWLEADER packet to get
        // acknowledged
        try {
            waitForNewLeaderAck(self.getId(), zk.getZxid());
        } catch (InterruptedException e) {
            shutdown("Waiting for a quorum of followers, only synced with sids: [ "
                    + getSidSetString(newLeaderProposal.ackSet) + " ]");
            HashSet<Long> followerSet = new HashSet<Long>();
            for (LearnerHandler f : learners)
                followerSet.add(f.getSid());
                
            if (self.getQuorumVerifier().containsQuorum(followerSet)) {
                LOG.warn("Enough followers present. "
                        + "Perhaps the initTicks need to be increased.");
            }
            Thread.sleep(self.tickTime);
            self.tick.incrementAndGet();
            return;
        }
        
        startZkServer();
        
        /**
         * WARNING: do not use this for anything other than QA testing
         * on a real cluster. Specifically to enable verification that quorum
         * can handle the lower 32bit roll-over issue identified in
         * ZOOKEEPER-1277. Without this option it would take a very long
         * time (on order of a month say) to see the 4 billion writes
         * necessary to cause the roll-over to occur.
         * 
         * This field allows you to override the zxid of the server. Typically
         * you'll want to set it to something like 0xfffffff0 and then
         * start the quorum, run some operations and see the re-election.
         */
        String initialZxid = System.getProperty("zookeeper.testingonly.initialZxid");
        if (initialZxid != null) {
            long zxid = Long.parseLong(initialZxid);
            zk.setZxid((zk.getZxid() & 0xffffffff00000000L) | zxid);
        }
        
        if (!System.getProperty("zookeeper.leaderServes", "yes").equals("no")) {
            self.cnxnFactory.setZooKeeperServer(zk);
        }
        // Everything is a go, simply start counting the ticks
        // WARNING: I couldn't find any wait statement on a synchronized
        // block that would be notified by this notifyAll() call, so
        // I commented it out
        //synchronized (this) {
        //    notifyAll();
        //}
        // We ping twice a tick, so we only update the tick every other
        // iteration
        boolean tickSkip = true;

        while (true) {
            Thread.sleep(self.tickTime / 2);
            if (!tickSkip) {
                self.tick.incrementAndGet();
            }
            HashSet<Long> syncedSet = new HashSet<Long>();

            // lock on the followers when we use it.
            syncedSet.add(self.getId());

            for (LearnerHandler f : getLearners()) {
                // Synced set is used to check we have a supporting quorum, so only
                // PARTICIPANT, not OBSERVER, learners should be used
                if (f.synced() && f.getLearnerType() == LearnerType.PARTICIPANT) {
                    syncedSet.add(f.getSid());
                }
                f.ping();
            }

            // check leader running status
            if (!this.isRunning()) {
                shutdown("Unexpected internal error");
                return;
            }

          if (!tickSkip && !self.getQuorumVerifier().containsQuorum(syncedSet)) {
            //if (!tickSkip && syncedCount < self.quorumPeers.size() / 2) {
                // Lost quorum, shutdown
                shutdown("Not sufficient followers synced, only synced with sids: [ "
                        + getSidSetString(syncedSet) + " ]");
                // make sure the order is the same!
                // the leader goes to looking
                return;
          } 
          tickSkip = !tickSkip;
        }
    } finally {
        zk.unregisterJMX(this);
    }
}
```

org.apache.zookeeper.server.quorum.Leader.LearnerCnxAcceptor#run

```java
public void run() {
    try {
        while (!stop) {
            try{
                Socket s = ss.accept();
                // start with the initLimit, once the ack is processed
                // in LearnerHandler switch to the syncLimit
                s.setSoTimeout(self.tickTime * self.initLimit);
                s.setTcpNoDelay(nodelay);

                BufferedInputStream is = new BufferedInputStream(
                        s.getInputStream());
              	// 连接成功，开启io线程
                LearnerHandler fh = new LearnerHandler(s, is, Leader.this);
                fh.start();
            } catch (SocketException e) {
                if (stop) {
                    LOG.info("exception while shutting down acceptor: "
                            + e);

                    // When Leader.shutdown() calls ss.close(),
                    // the call to accept throws an exception.
                    // We catch and set stop to true.
                    stop = true;
                } else {
                    throw e;
                }
            } catch (SaslException e){
                LOG.error("Exception while connecting to quorum learner", e);
            }
        }
    } catch (Exception e) {
        LOG.warn("Exception while accepting follower", e);
    }
}
```

## FOLLOWING

```java
case FOLLOWING:
    try {
        LOG.info("FOLLOWING");
        setFollower(makeFollower(logFactory));
        follower.followLeader();
    } catch (Exception e) {
        LOG.warn("Unexpected exception",e);
    } finally {
        follower.shutdown();
        setFollower(null);
        setPeerState(ServerState.LOOKING);
    }
    break;
```

```java
void followLeader() throws InterruptedException {
    self.end_fle = Time.currentElapsedTime();
    long electionTimeTaken = self.end_fle - self.start_fle;
    self.setElectionTimeTaken(electionTimeTaken);
    LOG.info("FOLLOWING - LEADER ELECTION TOOK - {}", electionTimeTaken);
    self.start_fle = 0;
    self.end_fle = 0;
    fzk.registerJMX(new FollowerBean(this, zk), self.jmxLocalPeerBean);
    try {
        QuorumServer leaderServer = findLeader();            
        try {
          	// 连接leader
            connectToLeader(leaderServer.addr, leaderServer.hostname);
            long newEpochZxid = registerWithLeader(Leader.FOLLOWERINFO);

            //check to see if the leader zxid is lower than ours
            //this should never happen but is just a safety check
            long newEpoch = ZxidUtils.getEpochFromZxid(newEpochZxid);
            if (newEpoch < self.getAcceptedEpoch()) {
                LOG.error("Proposed leader epoch " + ZxidUtils.zxidToString(newEpochZxid)
                        + " is less than our accepted epoch " + ZxidUtils.zxidToString(self.getAcceptedEpoch()));
                throw new IOException("Error: Epoch of leader is lower");
            }
            syncWithLeader(newEpochZxid);                
            QuorumPacket qp = new QuorumPacket();
            while (this.isRunning()) {
                readPacket(qp);
                processPacket(qp);
            }
        } catch (Exception e) {
            LOG.warn("Exception when following the leader", e);
            try {
                sock.close();
            } catch (IOException e1) {
                e1.printStackTrace();
            }

            // clear pending revalidations
            pendingRevalidations.clear();
        }
    } finally {
        zk.unregisterJMX((Learner)this);
    }
}
```

```java
protected void connectToLeader(InetSocketAddress addr, String hostname)
        throws IOException, ConnectException, InterruptedException {
    sock = new Socket();        
    sock.setSoTimeout(self.tickTime * self.initLimit);
    for (int tries = 0; tries < 5; tries++) {
        try {
            sock.connect(addr, self.tickTime * self.syncLimit);
            sock.setTcpNoDelay(nodelay);
            break;
        } catch (IOException e) {
            if (tries == 4) {
                LOG.error("Unexpected exception",e);
                throw e;
            } else {
                LOG.warn("Unexpected exception, tries="+tries+
                        ", connecting to " + addr,e);
                sock = new Socket();
                sock.setSoTimeout(self.tickTime * self.initLimit);
            }
        }
        Thread.sleep(1000);
    }

    self.authLearner.authenticate(sock, hostname);

    leaderIs = BinaryInputArchive.getArchive(new BufferedInputStream(
            sock.getInputStream()));
    bufferedOutput = new BufferedOutputStream(sock.getOutputStream());
    leaderOs = BinaryOutputArchive.getArchive(bufferedOutput);
}   
```

## 数据同步

### leader

org.apache.zookeeper.server.quorum.LearnerHandler#run

一个follower对应一个learnerHandler线程

```java
public void run() {
    try {
        leader.addLearnerHandler(this);
        tickOfNextAckDeadline = leader.self.tick.get()
                + leader.self.initLimit + leader.self.syncLimit;

        ia = BinaryInputArchive.getArchive(bufferedInput);
        bufferedOutput = new BufferedOutputStream(sock.getOutputStream());
        oa = BinaryOutputArchive.getArchive(bufferedOutput);

        QuorumPacket qp = new QuorumPacket();
        ia.readRecord(qp, "packet");
        if(qp.getType() != Leader.FOLLOWERINFO && qp.getType() != Leader.OBSERVERINFO){
           LOG.error("First packet " + qp.toString()
                    + " is not FOLLOWERINFO or OBSERVERINFO!");
            return;
        }
        byte learnerInfoData[] = qp.getData();
        if (learnerInfoData != null) {
           if (learnerInfoData.length == 8) {
              ByteBuffer bbsid = ByteBuffer.wrap(learnerInfoData);
              this.sid = bbsid.getLong();
           } else {
              LearnerInfo li = new LearnerInfo();
              ByteBufferInputStream.byteBuffer2Record(ByteBuffer.wrap(learnerInfoData), li);
              this.sid = li.getServerid();
              this.version = li.getProtocolVersion();
           }
        } else {
           this.sid = leader.followerCounter.getAndDecrement();
        }

        LOG.info("Follower sid: " + sid + " : info : "
                + leader.self.quorumPeers.get(sid));
                    
        if (qp.getType() == Leader.OBSERVERINFO) {
              learnerType = LearnerType.OBSERVER;
        }            
        
        long lastAcceptedEpoch = ZxidUtils.getEpochFromZxid(qp.getZxid());
        
        long peerLastZxid;
        StateSummary ss = null;
        long zxid = qp.getZxid();
        long newEpoch = leader.getEpochToPropose(this.getSid(), lastAcceptedEpoch);
        
        if (this.getVersion() < 0x10000) {
            // we are going to have to extrapolate the epoch information
            long epoch = ZxidUtils.getEpochFromZxid(zxid);
            ss = new StateSummary(epoch, zxid);
            // fake the message
            leader.waitForEpochAck(this.getSid(), ss);
        } else {
            byte ver[] = new byte[4];
            ByteBuffer.wrap(ver).putInt(0x10000);
            QuorumPacket newEpochPacket = new QuorumPacket(Leader.LEADERINFO, ZxidUtils.makeZxid(newEpoch, 0), ver, null);
            oa.writeRecord(newEpochPacket, "packet");
            bufferedOutput.flush();
            QuorumPacket ackEpochPacket = new QuorumPacket();
            ia.readRecord(ackEpochPacket, "packet");
            if (ackEpochPacket.getType() != Leader.ACKEPOCH) {
                LOG.error(ackEpochPacket.toString()
                        + " is not ACKEPOCH");
                return;
}
            ByteBuffer bbepoch = ByteBuffer.wrap(ackEpochPacket.getData());
            ss = new StateSummary(bbepoch.getInt(), ackEpochPacket.getZxid());
            leader.waitForEpochAck(this.getSid(), ss);
        }
        peerLastZxid = ss.getLastZxid();
        
        /* the default to send to the follower */
        int packetToSend = Leader.SNAP;
        long zxidToSend = 0;
        long leaderLastZxid = 0;
        /** the packets that the follower needs to get updates from **/
        long updates = peerLastZxid;
        
        /* we are sending the diff check if we have proposals in memory to be able to 
         * send a diff to the 
         */ 
        ReentrantReadWriteLock lock = leader.zk.getZKDatabase().getLogLock();
        ReadLock rl = lock.readLock();
        try {
            rl.lock();        
            final long maxCommittedLog = leader.zk.getZKDatabase().getmaxCommittedLog();
            final long minCommittedLog = leader.zk.getZKDatabase().getminCommittedLog();
            LOG.info("Synchronizing with Follower sid: " + sid
                    +" maxCommittedLog=0x"+Long.toHexString(maxCommittedLog)
                    +" minCommittedLog=0x"+Long.toHexString(minCommittedLog)
                    +" peerLastZxid=0x"+Long.toHexString(peerLastZxid));

            LinkedList<Proposal> proposals = leader.zk.getZKDatabase().getCommittedLog();

            if (peerLastZxid == leader.zk.getZKDatabase().getDataTreeLastProcessedZxid()) {
                // Follower is already sync with us, send empty diff
                LOG.info("leader and follower are in sync, zxid=0x{}",
                        Long.toHexString(peerLastZxid));
                packetToSend = Leader.DIFF;
                zxidToSend = peerLastZxid;
            } else if (proposals.size() != 0) {
                LOG.debug("proposal size is {}", proposals.size());
                if ((maxCommittedLog >= peerLastZxid)
                        && (minCommittedLog <= peerLastZxid)) {
                    LOG.debug("Sending proposals to follower");

                    // as we look through proposals, this variable keeps track of previous
                    // proposal Id.
                    long prevProposalZxid = minCommittedLog;

                    // Keep track of whether we are about to send the first packet.
                    // Before sending the first packet, we have to tell the learner
                    // whether to expect a trunc or a diff
                    boolean firstPacket=true;

                    // If we are here, we can use committedLog to sync with
                    // follower. Then we only need to decide whether to
                    // send trunc or not
                    packetToSend = Leader.DIFF;
                    zxidToSend = maxCommittedLog;

                    for (Proposal propose: proposals) {
                        // skip the proposals the peer already has
                        if (propose.packet.getZxid() <= peerLastZxid) {
                            prevProposalZxid = propose.packet.getZxid();
                            continue;
                        } else {
                            // If we are sending the first packet, figure out whether to trunc
                            // in case the follower has some proposals that the leader doesn't
                            if (firstPacket) {
                                firstPacket = false;
                                // Does the peer have some proposals that the leader hasn't seen yet
                                if (prevProposalZxid < peerLastZxid) {
                                    // send a trunc message before sending the diff
                                    packetToSend = Leader.TRUNC;                                        
                                    zxidToSend = prevProposalZxid;
                                    updates = zxidToSend;
                                }
                            }
                            queuePacket(propose.packet);
                            QuorumPacket qcommit = new QuorumPacket(Leader.COMMIT, propose.packet.getZxid(),
                                    null, null);
                            queuePacket(qcommit);
                        }
                    }
                } else if (peerLastZxid > maxCommittedLog) {
                    LOG.debug("Sending TRUNC to follower zxidToSend=0x{} updates=0x{}",
                            Long.toHexString(maxCommittedLog),
                            Long.toHexString(updates));

                    packetToSend = Leader.TRUNC;
                    zxidToSend = maxCommittedLog;
                    updates = zxidToSend;
                } else {
                    LOG.warn("Unhandled proposal scenario");
                }
            } else {
                // just let the state transfer happen
                LOG.debug("proposals is empty");
            }               

            LOG.info("Sending " + Leader.getPacketType(packetToSend));
            leaderLastZxid = leader.startForwarding(this, updates);

        } finally {
            rl.unlock();
        }

         QuorumPacket newLeaderQP = new QuorumPacket(Leader.NEWLEADER,
                ZxidUtils.makeZxid(newEpoch, 0), null, null);
         if (getVersion() < 0x10000) {
            oa.writeRecord(newLeaderQP, "packet");
        } else {
            queuedPackets.add(newLeaderQP);
        }
        bufferedOutput.flush();
        //Need to set the zxidToSend to the latest zxid
        if (packetToSend == Leader.SNAP) {
            zxidToSend = leader.zk.getZKDatabase().getDataTreeLastProcessedZxid();
        }
        oa.writeRecord(new QuorumPacket(packetToSend, zxidToSend, null, null), "packet");
        bufferedOutput.flush();
        
        /* if we are not truncating or sending a diff just send a snapshot */
        if (packetToSend == Leader.SNAP) {
          	// 发送snap数据
            LOG.info("Sending snapshot last zxid of peer is 0x"
                    + Long.toHexString(peerLastZxid) + " " 
                    + " zxid of leader is 0x"
                    + Long.toHexString(leaderLastZxid)
                    + "sent zxid of db as 0x" 
                    + Long.toHexString(zxidToSend));
            // Dump data to peer
            leader.zk.getZKDatabase().serializeSnapshot(oa);
            oa.writeString("BenWasHere", "signature");
        }
        bufferedOutput.flush();
        
        // Start sending packets
        new Thread() {
            public void run() {
                Thread.currentThread().setName(
                        "Sender-" + sock.getRemoteSocketAddress());
                try {
                    sendPackets();
                } catch (InterruptedException e) {
                    LOG.warn("Unexpected interruption",e);
                }
            }
        }.start();
        
        /*
         * Have to wait for the first ACK, wait until 
         * the leader is ready, and only then we can
         * start processing messages.
         */
        qp = new QuorumPacket();
        ia.readRecord(qp, "packet");
        if(qp.getType() != Leader.ACK){
            LOG.error("Next packet was supposed to be an ACK");
            return;
        }
        LOG.info("Received NEWLEADER-ACK message from " + getSid());
        leader.waitForNewLeaderAck(getSid(), qp.getZxid());

        syncLimitCheck.start();
        
        // now that the ack has been processed expect the syncLimit
        sock.setSoTimeout(leader.self.tickTime * leader.self.syncLimit);

        /*
         * Wait until leader starts up
         */
        synchronized(leader.zk){
            while(!leader.zk.isRunning() && !this.isInterrupted()){
                leader.zk.wait(20);
            }
        }
        // Mutation packets will be queued during the serialize,
        // so we need to mark when the peer can actually start
        // using the data
        //
        queuedPackets.add(new QuorumPacket(Leader.UPTODATE, -1, null, null));

      	// 处理follower的请求
        while (true) {
            qp = new QuorumPacket();
            ia.readRecord(qp, "packet");

            long traceMask = ZooTrace.SERVER_PACKET_TRACE_MASK;
            if (qp.getType() == Leader.PING) {
                traceMask = ZooTrace.SERVER_PING_TRACE_MASK;
            }
            if (LOG.isTraceEnabled()) {
                ZooTrace.logQuorumPacket(LOG, traceMask, 'i', qp);
            }
            tickOfNextAckDeadline = leader.self.tick.get() + leader.self.syncLimit;


            ByteBuffer bb;
            long sessionId;
            int cxid;
            int type;

            switch (qp.getType()) {
            case Leader.ACK:
                if (this.learnerType == LearnerType.OBSERVER) {
                    if (LOG.isDebugEnabled()) {
                        LOG.debug("Received ACK from Observer  " + this.sid);
                    }
                }
                syncLimitCheck.updateAck(qp.getZxid());
                leader.processAck(this.sid, qp.getZxid(), sock.getLocalSocketAddress());
                break;
            case Leader.PING:
                // Process the touches
                ByteArrayInputStream bis = new ByteArrayInputStream(qp
                        .getData());
                DataInputStream dis = new DataInputStream(bis);
                while (dis.available() > 0) {
                    long sess = dis.readLong();
                    int to = dis.readInt();
                    leader.zk.touch(sess, to);
                }
                break;
            case Leader.REVALIDATE:
                bis = new ByteArrayInputStream(qp.getData());
                dis = new DataInputStream(bis);
                long id = dis.readLong();
                int to = dis.readInt();
                ByteArrayOutputStream bos = new ByteArrayOutputStream();
                DataOutputStream dos = new DataOutputStream(bos);
                dos.writeLong(id);
                boolean valid = leader.zk.touch(id, to);
                if (valid) {
                    try {
                        //set the session owner
                        // as the follower that
                        // owns the session
                        leader.zk.setOwner(id, this);
                    } catch (SessionExpiredException e) {
                        LOG.error("Somehow session " + Long.toHexString(id) + " expired right after being renewed! (impossible)", e);
                    }
                }
                if (LOG.isTraceEnabled()) {
                    ZooTrace.logTraceMessage(LOG,
                                             ZooTrace.SESSION_TRACE_MASK,
                                             "Session 0x" + Long.toHexString(id)
                                             + " is valid: "+ valid);
                }
                dos.writeBoolean(valid);
                qp.setData(bos.toByteArray());
                queuedPackets.add(qp);
                break;
            case Leader.REQUEST:  
                // follower遇到写请求，通知leader处理
                bb = ByteBuffer.wrap(qp.getData());
                sessionId = bb.getLong();
                cxid = bb.getInt();
                type = bb.getInt();
                bb = bb.slice();
                Request si;
                if(type == OpCode.sync){
                    si = new LearnerSyncRequest(this, sessionId, cxid, type, bb, qp.getAuthinfo());
                } else {
                    si = new Request(null, sessionId, cxid, type, bb, qp.getAuthinfo());
                }
                si.setOwner(this);
                leader.zk.submitRequest(si);
                break;
            default:
                LOG.warn("unexpected quorum packet, type: {}", packetToString(qp));
                break;
            }
        }
    } catch (IOException e) {
        if (sock != null && !sock.isClosed()) {
            LOG.error("Unexpected exception causing shutdown while sock "
                    + "still open", e);
           //close the socket to make sure the 
           //other side can see it being close
           try {
              sock.close();
           } catch(IOException ie) {
              // do nothing
           }
        }
    } catch (InterruptedException e) {
        LOG.error("Unexpected exception causing shutdown", e);
    } finally {
        LOG.warn("******* GOODBYE " 
                + (sock != null ? sock.getRemoteSocketAddress() : "<null>")
                + " ********");
        shutdown();
    }
}
```

### follower

org.apache.zookeeper.server.quorum.Learner#syncWithLeader

```java
protected void syncWithLeader(long newLeaderZxid) throws IOException, InterruptedException{
    QuorumPacket ack = new QuorumPacket(Leader.ACK, 0, null, null);
    QuorumPacket qp = new QuorumPacket();
    long newEpoch = ZxidUtils.getEpochFromZxid(newLeaderZxid);
    // In the DIFF case we don't need to do a snapshot because the transactions will sync on top of any existing snapshot
    // For SNAP and TRUNC the snapshot is needed to save that history
    boolean snapshotNeeded = true;
    readPacket(qp);
    LinkedList<Long> packetsCommitted = new LinkedList<Long>();
    LinkedList<PacketInFlight> packetsNotCommitted = new LinkedList<PacketInFlight>();
    synchronized (zk) {
        if (qp.getType() == Leader.DIFF) {
            LOG.info("Getting a diff from the leader 0x{}", Long.toHexString(qp.getZxid()));
            snapshotNeeded = false;
        }
        else if (qp.getType() == Leader.SNAP) {
            LOG.info("Getting a snapshot from leader 0x" + Long.toHexString(qp.getZxid()));
            // The leader is going to dump the database
            // clear our own database and read
            zk.getZKDatabase().clear();
            zk.getZKDatabase().deserializeSnapshot(leaderIs);
            String signature = leaderIs.readString("signature");
            if (!signature.equals("BenWasHere")) {
                LOG.error("Missing signature. Got " + signature);
                throw new IOException("Missing signature");                   
            }
            zk.getZKDatabase().setlastProcessedZxid(qp.getZxid());
        } else if (qp.getType() == Leader.TRUNC) {
            //we need to truncate the log to the lastzxid of the leader
            LOG.warn("Truncating log to get in sync with the leader 0x"
                    + Long.toHexString(qp.getZxid()));
            boolean truncated=zk.getZKDatabase().truncateLog(qp.getZxid());
            if (!truncated) {
                // not able to truncate the log
                LOG.error("Not able to truncate the log "
                        + Long.toHexString(qp.getZxid()));
                System.exit(13);
            }
            zk.getZKDatabase().setlastProcessedZxid(qp.getZxid());
        }
        else {
            LOG.error("Got unexpected packet from leader "
                    + qp.getType() + " exiting ... " );
            System.exit(13);

        }
        zk.createSessionTracker();
        
        long lastQueued = 0;

        // in Zab V1.0 (ZK 3.4+) we might take a snapshot when we get the NEWLEADER message, but in pre V1.0
        // we take the snapshot on the UPDATE message, since Zab V1.0 also gets the UPDATE (after the NEWLEADER)
        // we need to make sure that we don't take the snapshot twice.
        boolean isPreZAB1_0 = true;
        //If we are not going to take the snapshot be sure the transactions are not applied in memory
        // but written out to the transaction log
        boolean writeToTxnLog = !snapshotNeeded;
        // we are now going to start getting transactions to apply followed by an UPTODATE
        outerLoop:
        while (self.isRunning()) {
            readPacket(qp);
            switch(qp.getType()) {
            case Leader.PROPOSAL:
                PacketInFlight pif = new PacketInFlight();
                pif.hdr = new TxnHeader();
                pif.rec = SerializeUtils.deserializeTxn(qp.getData(), pif.hdr);
                if (pif.hdr.getZxid() != lastQueued + 1) {
                LOG.warn("Got zxid 0x"
                        + Long.toHexString(pif.hdr.getZxid())
                        + " expected 0x"
                        + Long.toHexString(lastQueued + 1));
                }
                lastQueued = pif.hdr.getZxid();
                packetsNotCommitted.add(pif);
                break;
            case Leader.COMMIT:
                if (!writeToTxnLog) {
                    pif = packetsNotCommitted.peekFirst();
                    if (pif.hdr.getZxid() != qp.getZxid()) {
                        LOG.warn("Committing " + qp.getZxid() + ", but next proposal is " + pif.hdr.getZxid());
                    } else {
                      	// 如果不需要保存事务log，则遇到commit，保存数据，两阶段提交，第一阶段发送数据，第二阶段发送处理数据对命令
                        zk.processTxn(pif.hdr, pif.rec);
                        packetsNotCommitted.remove();
                    }
                } else {
                    packetsCommitted.add(qp.getZxid());
                }
                break;
            case Leader.INFORM:
                /*
                 * Only observer get this type of packet. We treat this
                 * as receiving PROPOSAL and COMMMIT.
                 */
                PacketInFlight packet = new PacketInFlight();
                packet.hdr = new TxnHeader();
                packet.rec = SerializeUtils.deserializeTxn(qp.getData(), packet.hdr);
                // Log warning message if txn comes out-of-order
                if (packet.hdr.getZxid() != lastQueued + 1) {
                    LOG.warn("Got zxid 0x"
                            + Long.toHexString(packet.hdr.getZxid())
                            + " expected 0x"
                            + Long.toHexString(lastQueued + 1));
                }
                lastQueued = packet.hdr.getZxid();
                if (!writeToTxnLog) {
                    // Apply to db directly if we haven't taken the snapshot
                    zk.processTxn(packet.hdr, packet.rec);
                } else {
                    packetsNotCommitted.add(packet);
                    packetsCommitted.add(qp.getZxid());
                }
                break;
            case Leader.UPTODATE:
                // 同步结束
                if (isPreZAB1_0) {
                    zk.takeSnapshot();
                    self.setCurrentEpoch(newEpoch);
                }
                self.cnxnFactory.setZooKeeperServer(zk);                
                break outerLoop;
            case Leader.NEWLEADER: // Getting NEWLEADER here instead of in discovery 
                // means this is Zab 1.0
                // Create updatingEpoch file and remove it after current
                // epoch is set. QuorumPeer.loadDataBase() uses this file to
                // detect the case where the server was terminated after
                // taking a snapshot but before setting the current epoch.
                File updating = new File(self.getTxnFactory().getSnapDir(),
                                    QuorumPeer.UPDATING_EPOCH_FILENAME);
                if (!updating.exists() && !updating.createNewFile()) {
                    throw new IOException("Failed to create " +
                                          updating.toString());
                }
                if (snapshotNeeded) {
                    zk.takeSnapshot();
                }
                self.setCurrentEpoch(newEpoch);
                if (!updating.delete()) {
                    throw new IOException("Failed to delete " +
                                          updating.toString());
                }
                writeToTxnLog = true; //Anything after this needs to go to the transaction log, not applied directly in memory
                isPreZAB1_0 = false;
                writePacket(new QuorumPacket(Leader.ACK, newLeaderZxid, null, null), true);
                break;
            }
        }
    }
    ack.setZxid(ZxidUtils.makeZxid(newEpoch, 0));
    writePacket(ack, true);
    sock.setSoTimeout(self.tickTime * self.syncLimit);
  	// 启动服务，接听客户端请求
    zk.startup();
    /*
     * Update the election vote here to ensure that all members of the
     * ensemble report the same vote to new servers that start up and
     * send leader election notifications to the ensemble.
     * 
     * @see https://issues.apache.org/jira/browse/ZOOKEEPER-1732
     */
    self.updateElectionVote(newEpoch);

    // We need to log the stuff that came in between the snapshot and the uptodate
    if (zk instanceof FollowerZooKeeperServer) {
        FollowerZooKeeperServer fzk = (FollowerZooKeeperServer)zk;
        for(PacketInFlight p: packetsNotCommitted) {
          	// 写事务log
            fzk.logRequest(p.hdr, p.rec);
        }
        for(Long zxid: packetsCommitted) {
          	// 事务提交，保存数据
            fzk.commit(zxid);
        }
    } else if (zk instanceof ObserverZooKeeperServer) {
        // Similar to follower, we need to log requests between the snapshot
        // and UPTODATE
        ObserverZooKeeperServer ozk = (ObserverZooKeeperServer) zk;
        for (PacketInFlight p : packetsNotCommitted) {
            Long zxid = packetsCommitted.peekFirst();
            if (p.hdr.getZxid() != zxid) {
                // log warning message if there is no matching commit
                // old leader send outstanding proposal to observer
                LOG.warn("Committing " + Long.toHexString(zxid)
                        + ", but next proposal is "
                        + Long.toHexString(p.hdr.getZxid()));
                continue;
            }
            packetsCommitted.remove();
            Request request = new Request(null, p.hdr.getClientId(),
                    p.hdr.getCxid(), p.hdr.getType(), null, null);
            request.txn = p.rec;
            request.hdr = p.hdr;
            ozk.commitRequest(request);
        }
    } else {
        // New server type need to handle in-flight packets
        throw new UnsupportedOperationException("Unknown server type");
    }
}
```

## 接听客户端请求

### leader

org.apache.zookeeper.server.quorum.Leader#lead

```java
startZkServer();
```

org.apache.zookeeper.server.quorum.Leader#startZkServer

```java
private synchronized void startZkServer() {
    // Update lastCommitted and Db's zxid to a value representing the new epoch
    lastCommitted = zk.getZxid();
    LOG.info("Have quorum of supporters, sids: [ "
            + getSidSetString(newLeaderProposal.ackSet)
            + " ]; starting up and setting last processed zxid: 0x{}",
            Long.toHexString(zk.getZxid()));
    zk.startup();
    /*
     * Update the election vote here to ensure that all members of the
     * ensemble report the same vote to new servers that start up and
     * send leader election notifications to the ensemble.
     * 
     * @see https://issues.apache.org/jira/browse/ZOOKEEPER-1732
     */
    self.updateElectionVote(getEpoch());

    zk.getZKDatabase().setlastProcessedZxid(zk.getZxid());
}
```

org.apache.zookeeper.server.quorum.LeaderZooKeeperServer#setupRequestProcessors

```java
protected void setupRequestProcessors() {
    RequestProcessor finalProcessor = new FinalRequestProcessor(this);
    RequestProcessor toBeAppliedProcessor = new Leader.ToBeAppliedRequestProcessor(
            finalProcessor, getLeader().toBeApplied);
    commitProcessor = new CommitProcessor(toBeAppliedProcessor,
            Long.toString(getServerId()), false,
            getZooKeeperServerListener());
    commitProcessor.start();
    ProposalRequestProcessor proposalProcessor = new ProposalRequestProcessor(this,
            commitProcessor);
    proposalProcessor.initialize();
    firstProcessor = new PrepRequestProcessor(this, proposalProcessor);
    ((PrepRequestProcessor)firstProcessor).start();
}
```

PrepRequestProcessor：acl，构造txn

ProposalRequestProcessor

CommitProcessor

ToBeAppliedRequestProcessor

FinalRequestProcessor：更新内存，返回response



SyncRequestProcessor：持久txn，快照

AckRequestProcessor



流程：

commitprocessor，阻塞

proposalprocessor提议follower处理相同事务

持久化processor

处理follower的回复ack，ack达到半数以上

发送commit给follower，唤醒commitprocessor的阻塞

然后到下一个处理起处理

### follower

org.apache.zookeeper.server.quorum.Learner#syncWithLeader

```java
zk.startup();
```

org.apache.zookeeper.server.ZooKeeperServer#startup

```java
public synchronized void startup() {
    if (sessionTracker == null) {
        createSessionTracker();
    }
    startSessionTracker();
    setupRequestProcessors();

    registerJMX();

    setState(State.RUNNING);
    notifyAll();
}
```

org.apache.zookeeper.server.quorum.FollowerZooKeeperServer#setupRequestProcessors

```java
protected void setupRequestProcessors() {
    RequestProcessor finalProcessor = new FinalRequestProcessor(this);
    commitProcessor = new CommitProcessor(finalProcessor,
            Long.toString(getServerId()), true,
            getZooKeeperServerListener());
    commitProcessor.start();
    firstProcessor = new FollowerRequestProcessor(this, commitProcessor);
    ((FollowerRequestProcessor) firstProcessor).start();
    syncProcessor = new SyncRequestProcessor(this,
            new SendAckRequestProcessor((Learner)getFollower()));
    syncProcessor.start();
}
```

FollowerRequestProcessor

CommitProcessor

FinalRequestProcessor



SyncRequestProcessor

SendAckRequestProcessor



commitprocecssor，阻塞

如果是事务请求，发送request给leader

## leading、follower请求交互

### leader



### follower

org.apache.zookeeper.server.quorum.Follower#followLeader

```java
void followLeader() throws InterruptedException {
    self.end_fle = Time.currentElapsedTime();
    long electionTimeTaken = self.end_fle - self.start_fle;
    self.setElectionTimeTaken(electionTimeTaken);
    LOG.info("FOLLOWING - LEADER ELECTION TOOK - {}", electionTimeTaken);
    self.start_fle = 0;
    self.end_fle = 0;
    fzk.registerJMX(new FollowerBean(this, zk), self.jmxLocalPeerBean);
    try {
        QuorumServer leaderServer = findLeader();            
        try {
            connectToLeader(leaderServer.addr, leaderServer.hostname);
            long newEpochZxid = registerWithLeader(Leader.FOLLOWERINFO);

            //check to see if the leader zxid is lower than ours
            //this should never happen but is just a safety check
            long newEpoch = ZxidUtils.getEpochFromZxid(newEpochZxid);
            if (newEpoch < self.getAcceptedEpoch()) {
                LOG.error("Proposed leader epoch " + ZxidUtils.zxidToString(newEpochZxid)
                        + " is less than our accepted epoch " + ZxidUtils.zxidToString(self.getAcceptedEpoch()));
                throw new IOException("Error: Epoch of leader is lower");
            }
            syncWithLeader(newEpochZxid);                
            QuorumPacket qp = new QuorumPacket();
            while (this.isRunning()) {
              	// 处理leader请求
                readPacket(qp);
                processPacket(qp);
            }
        } catch (Exception e) {
            LOG.warn("Exception when following the leader", e);
            try {
                sock.close();
            } catch (IOException e1) {
                e1.printStackTrace();
            }

            // clear pending revalidations
            pendingRevalidations.clear();
        }
    } finally {
        zk.unregisterJMX((Learner)this);
    }
}
```

## 持久化

syncRequestProcessor

```java
public void run() {
    try {
        int logCount = 0;

        // we do this in an attempt to ensure that not all of the servers
        // in the ensemble take a snapshot at the same time
        setRandRoll(r.nextInt(snapCount/2));
        while (true) {
            Request si = null;
            if (toFlush.isEmpty()) {
                si = queuedRequests.take();
            } else {
                si = queuedRequests.poll();
                if (si == null) {
                    flush(toFlush);
                    continue;
                }
            }
            if (si == requestOfDeath) {
                break;
            }
            if (si != null) {
                // track the number of records written to the log
                if (zks.getZKDatabase().append(si)) {
                    logCount++;
                    if (logCount > (snapCount / 2 + randRoll)) {
                        setRandRoll(r.nextInt(snapCount/2));
                        // roll the log
                        zks.getZKDatabase().rollLog();
                        // take a snapshot
                        if (snapInProcess != null && snapInProcess.isAlive()) {
                            LOG.warn("Too busy to snap, skipping");
                        } else {
                          	// 开启快照线程，将整个内存数据保存在文件
                            snapInProcess = new ZooKeeperThread("Snapshot Thread") {
                                    public void run() {
                                        try {
                                            zks.takeSnapshot();
                                        } catch(Exception e) {
                                            LOG.warn("Unexpected exception", e);
                                        }
                                    }
                                };
                            snapInProcess.start();
                        }
                        logCount = 0;
                    }
                } else if (toFlush.isEmpty()) {
                    // optimization for read heavy workloads
                    // iff this is a read, and there are no pending
                    // flushes (writes), then just pass this to the next
                    // processor
                    if (nextProcessor != null) {
                        nextProcessor.processRequest(si);
                        if (nextProcessor instanceof Flushable) {
                            ((Flushable)nextProcessor).flush();
                        }
                    }
                    continue;
                }
                toFlush.add(si);
                if (toFlush.size() > 1000) {
                  	// 1000个事务，一个文件
                    flush(toFlush);
                }
            }
        }
    } catch (Throwable t) {
        handleException(this.getName(), t);
        running = false;
    }
    LOG.info("SyncRequestProcessor exited!");
}
```

## server工作状态

LOOKING：当前Server不知道leader是谁，正在搜寻
LEADING：当前Server即为选举出来的leader
FOLLOWING：leader已经选举出来，当前Server与之同步

 ```
Follower主要有四个功能：
1. 向Leader发送请求（PING消息、REQUEST消息、ACK消息、REVALIDATE消息）；
2 .接收Leader消息并进行处理；
3 .接收Client的请求，如果为写请求，发送给Leader进行投票；
4 .返回Client结果。
Follower的消息循环处理如下几种来自Leader的消息：
1 .PING消息： 心跳消息；
2 .PROPOSAL消息：Leader发起的提案，要求Follower投票；
3 .COMMIT消息：服务器端最新一次提案的信息；
4 .UPTODATE消息：表明同步完成；
5 .REVALIDATE消息：根据Leader的REVALIDATE结果，关闭待revalidate的session还是允许其接受消息；
6 .SYNC消息：返回SYNC结果到客户端，这个消息最初由客户端发起，用来强制得到最新的更新。
 ```

## redis异同点

