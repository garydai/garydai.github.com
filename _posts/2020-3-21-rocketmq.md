---
date: 2020-3-21
layout: default
title: rocketmq

---

# rocketmq

## 整体框架

![image-20200322100408404](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200322100408404.png)

## 基本概念

**Message**
代表一条消息，使用messageId唯一识别，用户在发送时可以设置messageKey，便于之后查询和跟踪。RocketMQ不对消息的格式做限制，message body是二进制，序列化操作由用户完成。
**Topic**
topic用于将消息按主题做划分，producer将消息发往指定的topic，consumer订阅该topic就可以收到这条消息。Topic跟发送方和消费方都没有强关联关系，发送方可以同时往多个topic投放消息，消费方也可以订阅多个topic的消息。在RocketMQ中，topic是一个上逻辑概念。消息存储不会按topic分开。
**Queue**
topic和queue是1对多的关系，一个Topic下可以包含多个Queue，主要用于负载均衡。发送消息时，用户只指定topic，producer会根据topic的路由信息选择具体发到哪个Queue上。consumer订阅消息时，会根据负载均衡策略决定订阅哪些queue的消息。
**Offset**
RocketMQ在存储消息时会为每个topic下的每个Queue生成一个消息的索引文件，每个queue都对应一个offset记录当前queue中消息条数。

一个Topic拥有多个消息队列，一个Broker为每一主题默认创建4个读队列4 个写队列 

## 模块

**NameServer**
NameServer可以看作是RocketMQ的**注册中心**，它管理两部分数据：**集群的Topic-Queue的路由配置；Broker的实时配置信息**。其它模块通过Nameserv提供的接口获取最新的topic配置和路由信息。

- Producer/Consumer：通过查询接口获取topic对应的Broker的地址信息
- Broker：注册配置信息到nameserv， 实时更新topic信息到nameserv

**Broker**
Broker是RocketMQ的核心模块，负责接收并存储消息，同时提供Push/Pull接口来将消息发送给consumer。Consumer可选择从Master或者Slave读取数据。多个主/从组成Broker集群，**集群内的Master节点之间不做数据交互**。Broker同时提供消息查询的功能，可以通过MessageID和messageKey来查询消息。Borker会将自己的topic配置信息实时同步到nameserv。

**Producer**
消息的发送端，Producer位于用户的进程内，Producer通过NameServ获取所有broker的路由信息，根据负载均衡策略选择将消息发到哪个broker，然后调用broker接口提交消息。

**Consumer**
消息的消费端，位于用户进程内。Consumer通过向broker发送Pull请求来获取消息数据。如果consumer在请求时没有数据，Broker可以将请求暂时hold住不返回，等待新消息来的时候再回复，这就是Push模式。Consumer可以以两种模式启动，广播（Broadcast）和集群（Cluster），广播模式下，一条消息会发送给所有consumer，集群模式下消息只会发送给一个consumer

## 高可用

1、Nameserv的实现非常轻量化，每个服务都是无状态的，缓存了整个集群的全量数据，并且会将数据写入持久化到磁盘，任何一个节点的上线和下线都不影响数据的一致性。
2、Broker分为主节点和从节点，message的数据都写入master节点，Slave节点从master节点同步数据。因为只有主节点接收数据写入，所以在主节点挂掉后，无法再接收消息，但是客户端仍然可以从slave读取之前写入的消息。
通过将多个主从节点组合成一个集群，可以保证broker的高可用。在一个主节点挂掉后，producer可选择将数据发送到集群内其他主节点
3、Producer位于用户端，支持失败策略来决定消息优先发到哪个broker，可以及时排除已下线的broker
4、多个Consumer组成ConsumerGroup，在集群默认下，每个consumer负责消费一部分Queue的消息，当一个consumer下线后，group内的节点会重新做负载均衡，保证所有queue的消息都至少有一个consumer节点在消费。
5、Cluster模式下支持消息确认和重发，consumer消费成功后会将状态同步给broker。如果消费失败，broker会将消息重新发送，直到消费成功或者超过重发次数。

以上就是RocketMQ的基础概念和原理，后面会按模块来分析源码，讲到各个模块的具体实现。

## namesrv

NameServer 主要作用是为消息生产者和消息消费者提供关于主题 Topic 的路由信息，还要能够管理 Broker节点，包括路由注册、路由删除等功能。



```java
public NamesrvController(NamesrvConfig namesrvConfig, NettyServerConfig nettyServerConfig) {
        //nameserv参数配置
        this.namesrvConfig = namesrvConfig; 
        //netty的参数配置
        this.nettyServerConfig = nettyServerConfig;
        this.kvConfigManager = new KVConfigManager(this);
        //初始化RouteInfoManager
        this.routeInfoManager = new RouteInfoManager();
        //监听客户端连接(Channel)的变化，通知RouteInfoManager检查broker是否有变化
        this.brokerHousekeepingService = new BrokerHousekeepingService(this);
        this.configuration = new Configuration(
            log,
            this.namesrvConfig, this.nettyServerConfig
        );
        //Nameserv的配置参数会保存到磁盘文件中
        this.configuration.setStorePathFromConfig(this.namesrvConfig, "configStorePath");
    }
```

RouteInfoManager缓存整个集群的broker信息，以及topic和queue的配置信息。

```java
		//1、Topic和broker的Map，保存了topic在每个broker上的读写Queue的个数以及读写权限
    private final HashMap<String/* topic */, List<QueueData>> topicQueueTable;
    //2、注册到nameserv上的所有Broker，按照brokername分组
    private final HashMap<String/* brokerName */, BrokerData> brokerAddrTable;
    //3、broker的集群对应关系
    private final HashMap<String/* clusterName */, Set<String/* brokerName */>> clusterAddrTable;
    //4、broker最新的心跳时间和配置版本号
    private final HashMap<String/* brokerAddr */, BrokerLiveInfo> brokerLiveTable;
    //5、broker和FilterServer的对应关系
    private final HashMap<String/* brokerAddr */, List<String>/* Filter Server */> filterServerTable;
```

初始化

org.apache.rocketmq.namesrv.NamesrvController#initialize

```java
public boolean initialize() {
        //1、初始化KVConfigManager
        this.kvConfigManager.load();
        //2、初始化netty server
        this.remotingServer = new NettyRemotingServer(this.nettyServerConfig, this.brokerHousekeepingService);
        //3、客户端请求处理的线程池
        this.remotingExecutor =
            Executors.newFixedThreadPool(nettyServerConfig.getServerWorkerThreads(), new ThreadFactoryImpl("RemotingExecutorThread_"));
       //4、注册DefaultRequestProcessor，所有的客户端请求都会转给这个Processor来处理
        this.registerProcessor();
       //5、启动定时调度，每10秒钟扫描所有Broker，检查存活状态
         this.scheduledExecutorService.scheduleAtFixedRate(new Runnable() {

            @Override
            public void run() {
                NamesrvController.this.routeInfoManager.scanNotActiveBroker();
            }
        }, 5, 10, TimeUnit.SECONDS);
        //6、日志打印的调度器，定时打印kvConfigManager的内容      
        this.scheduledExecutorService.scheduleAtFixedRate(new Runnable() {

            @Override
            public void run() {
                NamesrvController.this.kvConfigManager.printAllPeriodically();
            }
        }, 1, 10, TimeUnit.MINUTES);
        //7、监听ssl证书文件变化，
        if (TlsSystemConfig.tlsMode != TlsMode.DISABLED) {
            // Register a listener to reload SslContext
            ...
        }

        return true;
    }
```

org.apache.rocketmq.namesrv.processor.DefaultRequestProcessor#processRequest

```java
public RemotingCommand processRequest(ChannelHandlerContext ctx,
        RemotingCommand request) throws RemotingCommandException {
        ...
        switch (request.getCode()) {
            ...
            //broker注册请求
            case RequestCode.REGISTER_BROKER:
                Version brokerVersion = MQVersion.value2Version(request.getVersion());
                if (brokerVersion.ordinal() >= MQVersion.Version.V3_0_11.ordinal()) {
                    return this.registerBrokerWithFilterServer(ctx, request);
                } else {
                    return this.registerBroker(ctx, request);
                }
             //Broker注销请求
            case RequestCode.UNREGISTER_BROKER:
                return this.unregisterBroker(ctx, request);
            //根据topic获取broker路由信息
            case RequestCode.GET_ROUTEINTO_BY_TOPIC:
                return this.getRouteInfoByTopic(ctx, request);
            //获取broker集群信息
            case RequestCode.GET_BROKER_CLUSTER_INFO:
                return this.getBrokerClusterInfo(ctx, request);
            case RequestCode.WIPE_WRITE_PERM_OF_BROKER:
                return this.wipeWritePermOfBroker(ctx, request);
            //获取所有topic信息
            case RequestCode.GET_ALL_TOPIC_LIST_FROM_NAMESERVER:
                return getAllTopicListFromNameserver(ctx, request);
            //删除topic
            case RequestCode.DELETE_TOPIC_IN_NAMESRV:
                return deleteTopicInNamesrv(ctx, request);
            ...
        }
        return null;
    }
```



![image-20200404183354313](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200404183354313.png)

![image-20200404183456670](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200404183456670.png)

![image-20200404192001713](https://github.com/garydai/garydai.github.com/raw/master/_posts/image-20200404192001713.png)

## broker

### 创建主题

如果指定4个messagequeue，则每个broker都会创建4个messagequeue，不像kafka，创建分区的时候是有分配策略的

### 接收Producer发送的消息

### 存储消息

org.apache.rocketmq.store.CommitLog#putMessage

```java
public PutMessageResult putMessage(final MessageExtBrokerInner msg) {
    // Set the storage time
    msg.setStoreTimestamp(System.currentTimeMillis());
    // Set the message body BODY CRC (consider the most appropriate setting
    // on the client)
    msg.setBodyCRC(UtilAll.crc32(msg.getBody()));
    // Back to Results
    AppendMessageResult result = null;

    StoreStatsService storeStatsService = this.defaultMessageStore.getStoreStatsService();

    String topic = msg.getTopic();
    int queueId = msg.getQueueId();

    final int tranType = MessageSysFlag.getTransactionValue(msg.getSysFlag());
    if (tranType == MessageSysFlag.TRANSACTION_NOT_TYPE
        || tranType == MessageSysFlag.TRANSACTION_COMMIT_TYPE) {
        // Delay Delivery
        if (msg.getDelayTimeLevel() > 0) {
            if (msg.getDelayTimeLevel() > this.defaultMessageStore.getScheduleMessageService().getMaxDelayLevel()) {
                msg.setDelayTimeLevel(this.defaultMessageStore.getScheduleMessageService().getMaxDelayLevel());
            }

            topic = ScheduleMessageService.SCHEDULE_TOPIC;
            queueId = ScheduleMessageService.delayLevel2QueueId(msg.getDelayTimeLevel());

            // Backup real topic, queueId
            MessageAccessor.putProperty(msg, MessageConst.PROPERTY_REAL_TOPIC, msg.getTopic());
            MessageAccessor.putProperty(msg, MessageConst.PROPERTY_REAL_QUEUE_ID, String.valueOf(msg.getQueueId()));
            msg.setPropertiesString(MessageDecoder.messageProperties2String(msg.getProperties()));

            msg.setTopic(topic);
            msg.setQueueId(queueId);
        }
    }

    InetSocketAddress bornSocketAddress = (InetSocketAddress) msg.getBornHost();
    if (bornSocketAddress.getAddress() instanceof Inet6Address) {
        msg.setBornHostV6Flag();
    }

    InetSocketAddress storeSocketAddress = (InetSocketAddress) msg.getStoreHost();
    if (storeSocketAddress.getAddress() instanceof Inet6Address) {
        msg.setStoreHostAddressV6Flag();
    }

    long elapsedTimeInLock = 0;

    MappedFile unlockMappedFile = null;
    MappedFile mappedFile = this.mappedFileQueue.getLastMappedFile();

    putMessageLock.lock(); //spin or ReentrantLock ,depending on store config
    try {
        long beginLockTimestamp = this.defaultMessageStore.getSystemClock().now();
        this.beginTimeInLock = beginLockTimestamp;

        // Here settings are stored timestamp, in order to ensure an orderly
        // global
        msg.setStoreTimestamp(beginLockTimestamp);

        if (null == mappedFile || mappedFile.isFull()) {
            mappedFile = this.mappedFileQueue.getLastMappedFile(0); // Mark: NewFile may be cause noise
        }
        if (null == mappedFile) {
            log.error("create mapped file1 error, topic: " + msg.getTopic() + " clientAddr: " + msg.getBornHostString());
            beginTimeInLock = 0;
            return new PutMessageResult(PutMessageStatus.CREATE_MAPEDFILE_FAILED, null);
        }

        result = mappedFile.appendMessage(msg, this.appendMessageCallback);
        switch (result.getStatus()) {
            case PUT_OK:
                break;
            case END_OF_FILE:
                unlockMappedFile = mappedFile;
                // Create a new file, re-write the message
                mappedFile = this.mappedFileQueue.getLastMappedFile(0);
                if (null == mappedFile) {
                    // XXX: warn and notify me
                    log.error("create mapped file2 error, topic: " + msg.getTopic() + " clientAddr: " + msg.getBornHostString());
                    beginTimeInLock = 0;
                    return new PutMessageResult(PutMessageStatus.CREATE_MAPEDFILE_FAILED, result);
                }
                result = mappedFile.appendMessage(msg, this.appendMessageCallback);
                break;
            case MESSAGE_SIZE_EXCEEDED:
            case PROPERTIES_SIZE_EXCEEDED:
                beginTimeInLock = 0;
                return new PutMessageResult(PutMessageStatus.MESSAGE_ILLEGAL, result);
            case UNKNOWN_ERROR:
                beginTimeInLock = 0;
                return new PutMessageResult(PutMessageStatus.UNKNOWN_ERROR, result);
            default:
                beginTimeInLock = 0;
                return new PutMessageResult(PutMessageStatus.UNKNOWN_ERROR, result);
        }

        elapsedTimeInLock = this.defaultMessageStore.getSystemClock().now() - beginLockTimestamp;
        beginTimeInLock = 0;
    } finally {
        putMessageLock.unlock();
    }

    if (elapsedTimeInLock > 500) {
        log.warn("[NOTIFYME]putMessage in lock cost time(ms)={}, bodyLength={} AppendMessageResult={}", elapsedTimeInLock, msg.getBody().length, result);
    }

    if (null != unlockMappedFile && this.defaultMessageStore.getMessageStoreConfig().isWarmMapedFileEnable()) {
        this.defaultMessageStore.unlockMappedFile(unlockMappedFile);
    }

    PutMessageResult putMessageResult = new PutMessageResult(PutMessageStatus.PUT_OK, result);

    // Statistics
    storeStatsService.getSinglePutMessageTopicTimesTotal(msg.getTopic()).incrementAndGet();
    storeStatsService.getSinglePutMessageTopicSizeTotal(topic).addAndGet(result.getWroteBytes());

    // 刷盘
    handleDiskFlush(result, putMessageResult, msg);
  	// 主从复制
    handleHA(result, putMessageResult, msg);

    return putMessageResult;
}
```

### 回复consumer的消息拉取请求

### master-slave之间的数据同步

### 提供查询消息的接口



## 消息存储

![image-20201203145609749](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20201203145609749.png)

```java
this.fileChannel = new RandomAccessFile(this.file, "rw").getChannel();
this.mappedByteBuffer = this.fileChannel.map(MapMode.READ_WRITE, 0, fileSize);
```

使用文件映射技术，将大文件映射在内存中



![image-20200404115222335](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200404115222335.png)

Kafka 以 Topic 作为文件存储的基本单元，即每个 Topic 有其对应的数据文件和索引文件。当存在大量 Topic 时，消息持久化逐渐变成一种随机写磁盘的行为，此时磁盘 IO 成为影响系统吞吐量的主要因素。针对上述问题，RocketMQ 首先将消息的写入转化为顺序写，即所有 Topic 的消息均写入同一个文件（CommitLog）。同时，由于消息仍需要以 Topic 为维度进行消费，因此 RocketMQ 基于 CommitLog 为每个 Topic 异步构建多个逻辑队列（ConsumeQueue）和索引信息（Index）：ConsumeQueue 记录了消息在 CommitLog 中的位置信息；给定 Topic 和消息 Key，索引文件（Index）提供消息检索的能力，主要在问题排查和数据统计等场景应用。ConsumeQueue 和 Index 的构建依然遵循顺序写。



### commitlog、MappedFileQueue、MappedFile

![image-20201203165845830](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20201203165845830.png)

### 刷盘

![image-20201204103820718](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20201204103820718.png)

## consumer

问题1： PullRequest对象在什么时候创建并加入到pullRequestQueue 中以便唤醒 PullMessageService 线程 。

重平衡，doRebalance

问题2：集群内多个消费者是如何负载主题下的多个消费队列，并且如果有新的消费者加入时，消息队列又会如何 重新分布 。

### consumerQueue

RocketMQ 基于主题订阅模式实现消息消费，消费者关心的是 一个主题下的所有消 息，但由于同一主题的消息不连续地存储在 commitlog 文件中，试想一下如果消息消费者直接从消息存储文件( commitlog)中去遍历查找订阅主题下的消息，效率将极其低下， RocketMQ 为了适应消息消费的检索需求，设计了消息消费队列文件( Consumequeue)，该文件可以看成是 Commitlog 关于消息消费的“索引”文件， 消息主题，第二级目录为主题的消息队列

![image-20200404142717270](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200404142717270.png)

consumerQueue条目

![image-20200404142839490](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200404142839490.png)



**采用定时任务1ms将消息位移写入consumerQueue和index，异步构建ReputMessageService**

```java
public void run() {
    DefaultMessageStore.log.info(this.getServiceName() + " service started");

    while (!this.isStopped()) {
        try {
            Thread.sleep(1);
            this.doReput();
        } catch (Exception e) {
            DefaultMessageStore.log.warn(this.getServiceName() + " service has exception. ", e);
        }
    }

    DefaultMessageStore.log.info(this.getServiceName() + " service end");
}
```

Consumer端每隔一段时间主动向broker发送拉消息请求，broker在收到Pull请求后，如果有消息就立即返回数据，Consumer端收到返回的消息后，再回调消费者设置的Listener方法。如果broker在收到Pull请求时，消息队列里没有数据，broker端会阻塞请求直到有数据传递或超时才返回。

当然，Consumer端是通过一个线程将阻塞队列`LinkedBlockingQueue`中的`PullRequest`发送到broker拉取消息，以防止Consumer一直被阻塞。而Broker端，在接收到Consumer的`PullRequest`时，如果发现没有消息，就会把`PullRequest`扔到ConcurrentHashMap中缓存起来。

broker在启动时，会启动一个线程不停的从ConcurrentHashMap取出`PullRequest`检查，直到有数据返回。



RocketMQ 每次拉取完消息都会将消息存储到 PullRequest 对象中的 ProcessQueue 中

接着将消息放进消费线程中去执行

```java
// 并发消息消费逻辑实现类
org.apache.rocketmq.client.impl.consumer.ConsumeMessageConcurrentlyService;
// 顺序消息消费逻辑实现类
org.apache.rocketmq.client.impl.consumer.ConsumeMessageOrderlyService;
```



DefaultPushConsumer启动

org.apache.rocketmq.client.impl.consumer.DefaultMQPushConsumerImpl#start

```java
public synchronized void start() throws MQClientException {
        switch (this.serviceState) {
            case CREATE_JUST:
                this.serviceState = ServiceState.START_FAILED;
                //1、基本的参数检查，group name不能是DEFAULT_CONSUMER
                this.checkConfig();
                //2、将DefaultMQPushConsumer的订阅信息copy到RebalanceService中
                //如果是cluster模式，如果订阅了topic,则自动订阅%RETRY%topic
                this.copySubscription();
                //3、修改InstanceName参数值为PID
                if (this.defaultMQPushConsumer.getMessageModel() == MessageModel.CLUSTERING) {
                    this.defaultMQPushConsumer.changeInstanceNameToPID();
                }
                //4、新建一个MQClientInstance,客户端管理类，所有的i/o类操作由它管理
                //缓存客户端和topic信息，各种service
                //一个进程只有一个实例
                this.mQClientFactory = MQClientManager.getInstance().getAndCreateMQClientInstance(this.defaultMQPushConsumer, this.rpcHook);
                this.rebalanceImpl.setConsumerGroup(this.defaultMQPushConsumer.getConsumerGroup());
                this.rebalanceImpl.setMessageModel(this.defaultMQPushConsumer.getMessageModel());
                //5、Queue分配策略，默认AVG
                this.rebalanceImpl.setAllocateMessageQueueStrategy(this.defaultMQPushConsumer.getAllocateMessageQueueStrategy());
                this.rebalanceImpl.setmQClientFactory(this.mQClientFactory);
                //6、PullRequest封装实现类，封装了和broker的通信接口
                this.pullAPIWrapper = new PullAPIWrapper(
                    mQClientFactory,
                    this.defaultMQPushConsumer.getConsumerGroup(), isUnitMode());
                //7、消息被客户端过滤时会回调hook
                this.pullAPIWrapper.registerFilterMessageHook(filterMessageHookList);
                //8、consumer客户端消费offset持久化接口
                if (this.defaultMQPushConsumer.getOffsetStore() != null) {
                    this.offsetStore = this.defaultMQPushConsumer.getOffsetStore();
                } else {
                    switch (this.defaultMQPushConsumer.getMessageModel()) {
                        case BROADCASTING://广播消息本地持久化offset
                            this.offsetStore = new LocalFileOffsetStore(this.mQClientFactory, this.defaultMQPushConsumer.getConsumerGroup());
                            break;
                        case CLUSTERING://集群模式持久化到broker
                            this.offsetStore = new RemoteBrokerOffsetStore(this.mQClientFactory, this.defaultMQPushConsumer.getConsumerGroup());
                            break;
                        default:
                            break;
                    }
                    this.defaultMQPushConsumer.setOffsetStore(this.offsetStore);
                }
                //9、如果是本地持久化会从文件中load
                this.offsetStore.load();
                //10、消费服务，顺序和并发消息逻辑不同,接收消息并调用listener消费，处理消费结果
                if (this.getMessageListenerInner() instanceof MessageListenerOrderly) {
                    this.consumeOrderly = true;
                    this.consumeMessageService =
                        new ConsumeMessageOrderlyService(this, (MessageListenerOrderly) this.getMessageListenerInner());
                } else if (this.getMessageListenerInner() instanceof MessageListenerConcurrently) {
                    this.consumeOrderly = false;
                    this.consumeMessageService =
                        new ConsumeMessageConcurrentlyService(this, (MessageListenerConcurrently) this.getMessageListenerInner());
                }
                //11、只启动了清理等待处理消息服务
                this.consumeMessageService.start();
                //12、注册（缓存）consumer，保证CID单例
                boolean registerOK = mQClientFactory.registerConsumer(this.defaultMQPushConsumer.getConsumerGroup(), this);
                if (!registerOK) {
                    this.serviceState = ServiceState.CREATE_JUST;
                    this.consumeMessageService.shutdown();
                    throw new MQClientException("The consumer group[" + this.defaultMQPushConsumer.getConsumerGroup()
                        + "] has been created before, specify another name please." + FAQUrl.suggestTodo(FAQUrl.GROUP_NAME_DUPLICATE_URL),
                        null);
                }
                //13、启动MQClientInstance，会启动PullMessageService和RebalanceService
                mQClientFactory.start();
                log.info("the consumer [{}] start OK.", this.defaultMQPushConsumer.getConsumerGroup());
                this.serviceState = ServiceState.RUNNING;
                break;
            case RUNNING:
            case START_FAILED:
            case SHUTDOWN_ALREADY:
                ...
                ...
            default:
                break;
        }
        //14、从NameServer更新topic路由和订阅信息
        this.updateTopicSubscribeInfoWhenSubscriptionChanged();
        this.mQClientFactory.checkClientInBroker();//如果是SQL过滤，检查broker是否支持SQL过滤
        //15、发送心跳，同步consumer配置到broker,同步FilterClass到FilterServer(PushConsumer)
        this.mQClientFactory.sendHeartbeatToAllBrokerWithLock();
        //16、做一次re-balance
        this.mQClientFactory.rebalanceImmediately();
    }
```



org.apache.rocketmq.client.impl.factory.MQClientInstance#start

```java
public void start() throws MQClientException {

    synchronized (this) {
        switch (this.serviceState) {
            case CREATE_JUST:
                this.serviceState = ServiceState.START_FAILED;
                // If not specified,looking address from name server
                if (null == this.clientConfig.getNamesrvAddr()) {
                    this.mQClientAPIImpl.fetchNameServerAddr();
                }
                // Start request-response channel
                this.mQClientAPIImpl.start();
                // Start various schedule tasks
                this.startScheduledTask();
                // Start pull service
                this.pullMessageService.start();
                // Start rebalance service
                this.rebalanceService.start();
                // Start push service
                this.defaultMQProducer.getDefaultMQProducerImpl().start(false);
                log.info("the client factory [{}] start OK", this.clientId);
                this.serviceState = ServiceState.RUNNING;
                break;
            case START_FAILED:
                throw new MQClientException("The Factory object[" + this.getClientId() + "] has been created before, and failed.", null);
            default:
                break;
        }
    }
}
```

定时任务

```java
private void startScheduledTask() {
    if (null == this.clientConfig.getNamesrvAddr()) {
        this.scheduledExecutorService.scheduleAtFixedRate(new Runnable() {

            @Override
            public void run() {
                try {
                    MQClientInstance.this.mQClientAPIImpl.fetchNameServerAddr();
                } catch (Exception e) {
                    log.error("ScheduledTask fetchNameServerAddr exception", e);
                }
            }
        }, 1000 * 10, 1000 * 60 * 2, TimeUnit.MILLISECONDS);
    }

    this.scheduledExecutorService.scheduleAtFixedRate(new Runnable() {

        @Override
        public void run() {
            try {
                MQClientInstance.this.updateTopicRouteInfoFromNameServer();
            } catch (Exception e) {
                log.error("ScheduledTask updateTopicRouteInfoFromNameServer exception", e);
            }
        }
    }, 10, this.clientConfig.getPollNameServerInterval(), TimeUnit.MILLISECONDS);

    this.scheduledExecutorService.scheduleAtFixedRate(new Runnable() {

        @Override
        public void run() {
            try {
                MQClientInstance.this.cleanOfflineBroker();
                MQClientInstance.this.sendHeartbeatToAllBrokerWithLock();
            } catch (Exception e) {
                log.error("ScheduledTask sendHeartbeatToAllBroker exception", e);
            }
        }
    }, 1000, this.clientConfig.getHeartbeatBrokerInterval(), TimeUnit.MILLISECONDS);

   // 保存消费进度，广播消息存在本地，集群消息上传到所有的broker
    this.scheduledExecutorService.scheduleAtFixedRate(new Runnable() {

        @Override
        public void run() {
            try {
                MQClientInstance.this.persistAllConsumerOffset();
            } catch (Exception e) {
                log.error("ScheduledTask persistAllConsumerOffset exception", e);
            }
        }
    }, 1000 * 10, this.clientConfig.getPersistConsumerOffsetInterval(), TimeUnit.MILLISECONDS);
		// 对于`PushConsumer`，根据负载调整本地处理消息的线程池corePool大小
    this.scheduledExecutorService.scheduleAtFixedRate(new Runnable() {

        @Override
        public void run() {
            try {
                MQClientInstance.this.adjustThreadPool();
            } catch (Exception e) {
                log.error("ScheduledTask adjustThreadPool exception", e);
            }
        }
    }, 1, 1, TimeUnit.MINUTES);
}
```

### rebalance

消费端会通过RebalanceService线程，20秒钟做一次基于topic下的所有队列负载

把topic下的queue按照一定的算法（分配的策略包含：平均分配、消费端配置等）平均分配给consumer

org.apache.rocketmq.client.impl.consumer.RebalanceService#run

```java
public void run() {
    log.info(this.getServiceName() + " service started");

    while (!this.isStopped()) {
        this.waitForRunning(waitInterval);
        this.mqClientFactory.doRebalance();
    }

    log.info(this.getServiceName() + " service end");
}
```

```java
public void doRebalance(final boolean isOrder) {
        //获取该consumer的订阅信息
        Map<String, SubscriptionData> subTable = this.getSubscriptionInner();
        if (subTable != null) {
            for (final Map.Entry<String, SubscriptionData> entry : subTable.entrySet()) {
                final String topic = entry.getKey();
                try {
                    //循环针对所有订阅的topic，做rebalance
                    this.rebalanceByTopic(topic, isOrder);
                } catch (Throwable e) {
                    if (!topic.startsWith(MixAll.RETRY_GROUP_TOPIC_PREFIX)) {
                        log.warn("rebalanceByTopic Exception", e);
                    }
                }
            }
        }
        //做完rebalance后，检查是否有的queue已经不归自己负责消费，是的话就释放缓存message的queue
        this.truncateMessageQueueNotMyTopic();
    }
```

```java
private void rebalanceByTopic(final String topic, final boolean isOrder) {
        switch (messageModel) {
            case BROADCASTING: {
                ...
                ...
                break;
            }
            case CLUSTERING: {
                //1、从路由信息中获取topic对应所有的Queue
                Set<MessageQueue> mqSet = this.topicSubscribeInfoTable.get(topic);
                //2、从broker获取所有同一个group的所有Consumer ID
                List<String> cidAll = this.mQClientFactory.findConsumerIdList(topic, consumerGroup);
                if (null == mqSet) {
                    if (!topic.startsWith(MixAll.RETRY_GROUP_TOPIC_PREFIX)) {
                        log.warn("doRebalance, {}, but the topic[{}] not exist.", consumerGroup, topic);
                    }
                }

                if (null == cidAll) {
                    log.warn("doRebalance, {} {}, get consumer id list failed", consumerGroup, topic);
                }

                if (mqSet != null && cidAll != null) {
                    List<MessageQueue> mqAll = new ArrayList<MessageQueue>();
                    mqAll.addAll(mqSet);
                   //3、将MQ和cid都排好序
                    Collections.sort(mqAll);
                    Collections.sort(cidAll);

                    AllocateMessageQueueStrategy strategy = this.allocateMessageQueueStrategy;
                    //4、按照初始化是指定的分配策略，获取分配的MQ列表
                    List<MessageQueue> allocateResult = null;
                    try {
                        allocateResult = strategy.allocate(
                            this.consumerGroup,
                            this.mQClientFactory.getClientId(),
                            mqAll,
                            cidAll);
                    } catch (Throwable e) {
                        log.error("AllocateMessageQueueStrategy.allocate Exception. allocateMessageQueueStrategyName={}", strategy.getName(),
                            e);
                        return;
                    }

                    Set<MessageQueue> allocateResultSet = new HashSet<MessageQueue>();
                    if (allocateResult != null) {
                        allocateResultSet.addAll(allocateResult);
                    }
                    //5、更新rebalanceImpl中的processQueue用来缓存收到的消息，对于新加入的Queue，提交一次PullRequest
                    boolean changed = this.updateProcessQueueTableInRebalance(topic, allocateResultSet, isOrder);
                    if (changed) {
                        ...
                        ...
                        //6、同步数据到broker，通过发送一次心跳实现
                        this.messageQueueChanged(topic, mqSet, allocateResultSet);
                    }
                }
                break;
            }
            default:
                break;
        }
    }
```

平均分配策略AllocateMessageQueueAveragely

```java
 @Override
    public List<MessageQueue> allocate(String consumerGroup, String currentCID, List<MessageQueue> mqAll,
        List<String> cidAll) {
        int index = cidAll.indexOf(currentCID);
        int mod = mqAll.size() % cidAll.size();
        //AVG size计算方法，mq数量<=consumer数量，size=1，这种情况是很少的
        //否则size=mq数量/consumer数量，余数是几则前几个consumer的size+1,这样所有的queue都会有consumer消费
        int averageSize =
            mqAll.size() <= cidAll.size() ? 1 : (mod > 0 && index < mod ? mqAll.size() / cidAll.size()
                + 1 : mqAll.size() / cidAll.size());
        int startIndex = (mod > 0 && index < mod) ? index * averageSize : index * averageSize + mod;
        int range = Math.min(averageSize, mqAll.size() - startIndex);
        //从第一个consumer开始分配，每个分avgSize个连续的Queue，
        for (int i = 0; i < range; i++) {
            result.add(mqAll.get((startIndex + i) % mqAll.size()));
        }
        return result;
    }
```

举例来说，如果现在有8个消息消费队列q1，q2，q3，q4，q5，q6，q7，q8，有3个消费者c1，c2，c3，那么根据该负载算法，消息队列分配如下：c1：q1，q2，q3；c2：q4，q5，q6；c3：q7，q8

RocketMQ提供其它的queue分配策略：

- AVG_BY_CIRCLE， 跟AVG类似，只是分到的queue不是连续的。c1：q1，q4，q7；c2：q2，q5，q8；c3： q3，q6
- CONSISTENT_HASH，使用一致性hash算法来分配Queue，用户需自定义虚拟节点的数量
- MACHINE_ROOM，将queue先按照broker划分几个computer room，不同的consumer只消费某几个broker上的消息
- CONFIG,用户启动时指定消费哪些Queue的消息



还有其他重平衡的触发点

接口触发，

1）收到broker的consumer list发生变化通知后需要重新做负载均衡，比如同一个group中新加入了consumer或者有consumer下线；

2）consumer启动的时候



通过上面的策略分配到queue之后，`RebalanceImpl`通过`updateProcessQueueTableInRebalance()`方法来检查新加入queue并提交pull请求。一个MessageQueue对应一个ProcessQueue。

主要思路是遍历当前负载队列集合，如果队列不在新分配队列集合中，需要将该队列停止消费并保存消费进度；遍历已分配的队列，如果队列不在队列负载表中(processQueueTable)则需要创建该队列拉取任务PullRequest，然后添加到PullMessageService线程的pullRequestQueue 中，PulIMessageService才会继续拉取任务

```java
private boolean updateProcessQueueTableInRebalance(final String topic, final Set<MessageQueue> mqSet,
        final boolean isOrder) {
        boolean changed = false;

        Iterator<Entry<MessageQueue, ProcessQueue>> it = this.processQueueTable.entrySet().iterator();
        while (it.hasNext()) {
            Entry<MessageQueue, ProcessQueue> next = it.next();
            MessageQueue mq = next.getKey();
            ProcessQueue pq = next.getValue();

            if (mq.getTopic().equals(topic)) {
                if (!mqSet.contains(mq)) {//不再消费这个Queue的消息
                    pq.setDropped(true);
                    if (this.removeUnnecessaryMessageQueue(mq, pq)) {//保存offset并
                        it.remove();
                        changed = true;
                        log.info("doRebalance, {}, remove unnecessary mq, {}", consumerGroup, mq);
                    }
                } else if (pq.isPullExpired()) {//超过max idle时间
                    switch (this.consumeType()) {
                        case CONSUME_ACTIVELY:
                            break;
                        case CONSUME_PASSIVELY:
                            pq.setDropped(true);
                            if (this.removeUnnecessaryMessageQueue(mq, pq)) {
                                it.remove();
                                changed = true;
                                log.error("[BUG]doRebalance, {}, remove unnecessary mq, {}, because pull is pause, so try to fixed it",
                                    consumerGroup, mq);
                            }
                            break;
                        default:
                            break;
                    }
                }
            }
        }

        List<PullRequest> pullRequestList = new ArrayList<PullRequest>();
        for (MessageQueue mq : mqSet) {
            if (!this.processQueueTable.containsKey(mq)) {//如果是新加入的Queue
                if (isOrder && !this.lock(mq)) {
                    log.warn("doRebalance, {}, add a new mq failed, {}, because lock failed", consumerGroup, mq);
                    continue;
                }
               //从offset store中移除过时的数据
                this.removeDirtyOffset(mq);
                ProcessQueue pq = new ProcessQueue();
               //获取起始消费offset
                long nextOffset = this.computePullFromWhere(mq);
                if (nextOffset >= 0) {
                   //为新的Queue初始化一个ProcessQueue，用来缓存收到的消息
                    ProcessQueue pre = this.processQueueTable.putIfAbsent(mq, pq);
                    if (pre != null) {
                        log.info("doRebalance, {}, mq already exists, {}", consumerGroup, mq);
                    } else {
                        log.info("doRebalance, {}, add a new mq, {}", consumerGroup, mq);
                        //对新加的queue初始化一个PullRequest
                        PullRequest pullRequest = new PullRequest();
                        pullRequest.setConsumerGroup(consumerGroup);
                        pullRequest.setNextOffset(nextOffset);
                        pullRequest.setMessageQueue(mq);
                        pullRequest.setProcessQueue(pq);
                        pullRequestList.add(pullRequest);
                        changed = true;
                    }
                } else {
                    log.warn("doRebalance, {}, add new mq failed, {}", consumerGroup, mq);
                }
            }
        }
        //分发pull request到PullMessageService,拉取消息
        this.dispatchPullRequest(pullRequestList);
        return changed;
    }
```

从以上的代码可以看出，`RebalanceImpl`每次都会检查分配到的queue列表，如果发现有新的queue加入，就会给这个queue初始化一个缓存队列，然后新发起一个`PullRequest`给`PullMessageService`执行。由此可见，新增的queue只有第一次Pull请求时`RebalanceImpl`发起的，后续请求是在broker返回数据后，处理线程发起的。

### 消息拉取服务`PullMessageService`

处理pullRequestQueue里的pullRequest

```java
public void run() {
    log.info(this.getServiceName() + " service started");

    while (!this.isStopped()) {
        try {
            PullRequest pullRequest = this.pullRequestQueue.take();
            this.pullMessage(pullRequest);
        } catch (InterruptedException ignored) {
        } catch (Exception e) {
            log.error("Pull Message Service Run Method exception", e);
        }
    }

    log.info(this.getServiceName() + " service end");
}
```

org.apache.rocketmq.client.impl.consumer.DefaultMQPushConsumerImpl#pullMessage

在消息返回后，会将消息放入`ProcessQueue`，然后通知`ConsumeMessageService`来异步处理消息，然后再次提交Pull请求。这样对于用户端来说，只有`ConsumeMessageService`回调listener这一步是可见的，其它都是透明的。

![image-20200405205808582](https://github.com/garydai/garydai.github.com/raw/master/_posts/image-20200405205808582.png)

### 消息处理`ConsumeMessageService`

消息处理的逻辑比较简单，就是回调Consumer启动时注册的Listener。无论Listener是否处理成功，消息都会从`ProcessQueue`中移除掉。

org.apache.rocketmq.client.impl.consumer.ConsumeMessageConcurrentlyService.ConsumeRequest#run

```java
public void run() {
    if (this.processQueue.isDropped()) {
        log.info("the message queue not be able to consume, because it's dropped. group={} {}", ConsumeMessageConcurrentlyService.this.consumerGroup, this.messageQueue);
        return;
    }

    MessageListenerConcurrently listener = ConsumeMessageConcurrentlyService.this.messageListener;
    ConsumeConcurrentlyContext context = new ConsumeConcurrentlyContext(messageQueue);
    ConsumeConcurrentlyStatus status = null;
    defaultMQPushConsumerImpl.resetRetryAndNamespace(msgs, defaultMQPushConsumer.getConsumerGroup());

    ConsumeMessageContext consumeMessageContext = null;
    if (ConsumeMessageConcurrentlyService.this.defaultMQPushConsumerImpl.hasHook()) {
        consumeMessageContext = new ConsumeMessageContext();
        consumeMessageContext.setNamespace(defaultMQPushConsumer.getNamespace());
        consumeMessageContext.setConsumerGroup(defaultMQPushConsumer.getConsumerGroup());
        consumeMessageContext.setProps(new HashMap<String, String>());
        consumeMessageContext.setMq(messageQueue);
        consumeMessageContext.setMsgList(msgs);
        consumeMessageContext.setSuccess(false);
        ConsumeMessageConcurrentlyService.this.defaultMQPushConsumerImpl.executeHookBefore(consumeMessageContext);
    }

    long beginTimestamp = System.currentTimeMillis();
    boolean hasException = false;
    ConsumeReturnType returnType = ConsumeReturnType.SUCCESS;
    try {
        if (msgs != null && !msgs.isEmpty()) {
            for (MessageExt msg : msgs) {
                MessageAccessor.setConsumeStartTimeStamp(msg, String.valueOf(System.currentTimeMillis()));
            }
        }
      	// 回调消费消息
        status = listener.consumeMessage(Collections.unmodifiableList(msgs), context);
    } catch (Throwable e) {
        log.warn("consumeMessage exception: {} Group: {} Msgs: {} MQ: {}",
                RemotingHelper.exceptionSimpleDesc(e),
                ConsumeMessageConcurrentlyService.this.consumerGroup,
                msgs,
                messageQueue);
        hasException = true;
    }
    long consumeRT = System.currentTimeMillis() - beginTimestamp;
    if (null == status) {
        if (hasException) {
            returnType = ConsumeReturnType.EXCEPTION;
        } else {
            returnType = ConsumeReturnType.RETURNNULL;
        }
    } else if (consumeRT >= defaultMQPushConsumer.getConsumeTimeout() * 60 * 1000) {
        returnType = ConsumeReturnType.TIME_OUT;
    } else if (ConsumeConcurrentlyStatus.RECONSUME_LATER == status) {
        returnType = ConsumeReturnType.FAILED;
    } else if (ConsumeConcurrentlyStatus.CONSUME_SUCCESS == status) {
        returnType = ConsumeReturnType.SUCCESS;
    }

    if (ConsumeMessageConcurrentlyService.this.defaultMQPushConsumerImpl.hasHook()) {
        consumeMessageContext.getProps().put(MixAll.CONSUME_CONTEXT_TYPE, returnType.name());
    }

    if (null == status) {
        log.warn("consumeMessage return null, Group: {} Msgs: {} MQ: {}",
                ConsumeMessageConcurrentlyService.this.consumerGroup,
                msgs,
                messageQueue);
        status = ConsumeConcurrentlyStatus.RECONSUME_LATER;
    }

    if (ConsumeMessageConcurrentlyService.this.defaultMQPushConsumerImpl.hasHook()) {
        consumeMessageContext.setStatus(status.toString());
        consumeMessageContext.setSuccess(ConsumeConcurrentlyStatus.CONSUME_SUCCESS == status);
        ConsumeMessageConcurrentlyService.this.defaultMQPushConsumerImpl.executeHookAfter(consumeMessageContext);
    }

    ConsumeMessageConcurrentlyService.this.getConsumerStatsManager()
            .incConsumeRT(ConsumeMessageConcurrentlyService.this.consumerGroup, messageQueue.getTopic(), consumeRT);

    if (!processQueue.isDropped()) {
        ConsumeMessageConcurrentlyService.this.processConsumeResult(status, context, this);
    } else {
        log.warn("processQueue is dropped without process consume result. messageQueue={}, msgs={}", messageQueue, msgs);
    }
}
```

我们看下对于Listener返回结果的处理方法。

```java
 public void processConsumeResult(  
				final ConsumeConcurrentlyStatus status,
        final ConsumeConcurrentlyContext context,
        final ConsumeRequest consumeRequest
    ) {
        int ackIndex = context.getAckIndex();

        if (consumeRequest.getMsgs().isEmpty())
            return;

        ...
        ...

        switch (this.defaultMQPushConsumer.getMessageModel()) {
            //broadcast模式，处理失败，不做处理
            case BROADCASTING:
                for (int i = ackIndex + 1; i < consumeRequest.getMsgs().size(); i++) {
                    MessageExt msg = consumeRequest.getMsgs().get(i);
                    log.warn("BROADCASTING, the message consume failed, drop it, {}", msg.toString());
                }
                break;
            case CLUSTERING:
                List<MessageExt> msgBackFailed = new ArrayList<MessageExt>(consumeRequest.getMsgs().size());
                for (int i = ackIndex + 1; i < consumeRequest.getMsgs().size(); i++) {
                    MessageExt msg = consumeRequest.getMsgs().get(i);
                    //Cluster模式，将消息发回broker重新发送
                    boolean result = this.sendMessageBack(msg, context);
                    if (!result) {
                        msg.setReconsumeTimes(msg.getReconsumeTimes() + 1);
                        msgBackFailed.add(msg);
                    }
                }

                if (!msgBackFailed.isEmpty()) {
                    consumeRequest.getMsgs().removeAll(msgBackFailed);
                    //发回broker失败，则再次尝试本地消费
                    this.submitConsumeRequestLater(msgBackFailed, consumeRequest.getProcessQueue(), consumeRequest.getMessageQueue());
                }
                break;
            default:
                break;
        }
        //将消费前缓存的消息清除
        long offset = consumeRequest.getProcessQueue().removeMessage(consumeRequest.getMsgs());
        //更新offset
        if (offset >= 0 && !consumeRequest.getProcessQueue().isDropped()) {
            this.defaultMQPushConsumerImpl.getOffsetStore().updateOffset(consumeRequest.getMessageQueue(), offset, true);
        }
    }
```

消息处理失败后，consumer会将消息发给broker，broker会根据重试次数来重新投递消息



### 顺序消费

1. ConsumeMessageOrderlyService类的start()方法，如果是集群消费，则启动定时任务，定时向broker发送批量锁住当前正在消费的队列集合的消息，具体是consumer端拿到正在消费的队列集合，发送锁住队列的消息至broker，broker端返回锁住成功的队列集合。consumer收到后，设置是否锁住标志位。 这里注意2个变量：consumer端的RebalanceImpl里的ConcurrentHashMap processQueueTable，是否锁住设置在ProcessQueue里。broker端的RebalanceLockManager里的ConcurrentHashMap mqLockTable，这里维护着全局队列锁。

2. ConsumeMessageOrderlyService.ConsumeRequest的run方法是消费消息，这里还有个MessageQueueLock。messageQueueLock，维护当前consumer端的本地队列锁。保证当前只有一个线程能够进行消费。

3. 拉到消息存入ProcessQueue，然后判断，本地是否获得锁，全局队列是否被锁住，然后从ProcessQueue里取出消息，用MessageListenerOrderly进行消费。 拉到消息后调用ProcessQueue.putMessage(final List msgs) 存入，具体是存入TreeMap msgTreeMap。 然后是调用ProcessQueue.takeMessags(final int batchSize)消费，具体是把msgTreeMap里消费过的消息，转移到TreeMap msgTreeMapTemp。
4. 本地消费的事务控制，ConsumeOrderlyStatus.SUCCESS（提交），ConsumeOrderlyStatus.SUSPEND_CURRENT_QUEUE_A_MOMENT（挂起一会再消费），在此之前还有一个变量ConsumeOrderlyContext context的setAutoCommit()是否自动提交。 当SUSPEND_CURRENT_QUEUE_A_MOMENT时，autoCommit设置为true或者false没有区别，本质跟消费相反，把消息从msgTreeMapTemp转移回msgTreeMap，等待下次消费。当SUCCESS时，autoCommit设置为true时比设置为false多做了2个动作，consumeRequest.getProcessQueue().commit()和this.defaultMQPushConsumerImpl.getOffsetStore().updateOffset(consumeRequest.getMessageQueue(),
   commitOffset, false);ProcessQueue.commit() ：本质是删除msgTreeMapTemp里的消息，msgTreeMapTemp里的消息在上面消费时从msgTreeMap转移过来的。this.defaultMQPushConsumerImpl.getOffsetStore().updateOffset() ：本质是把拉消息的偏移量更新到本地内存中，然后定时更新到broker。

​       那么少了这2个动作会怎么样呢，随着消息的消费进行，msgTreeMapTemp里的消息堆积越来越多，消费消息的偏移量一直没有更新到broker导致consumer每次重新启动后都要从头开始重复消费。 就算更新了offset到broker，那么msgTreeMapTemp里的消息堆积呢？不知道这算不算bug。 所以，还是把autoCommit设置为true吧。



消费线程池的队列里放的是task（ConsumeRequest），不是消息；线程从线程池里取出task，然后从processQueue里的msgTreeMap取早的消息，进行处理。所以后放入线程池队列的task先执行，也能保证消息被顺序消费。

### 消费位移

如果消息消费是集群模式，那么消息进度保存在 Broker 上; 如果是广播模式，那么消息消费进度存储在消费端

## producer

producer发送消息支持3种方式，同步、异步和Oneway。

- 同步发送：客户端提交消息到broker后会等待返回结果，相对来说是最常用的方式。
- 异步发送：调用发送接口时会注册一个callback类，发送线程继续其它业务逻辑，producer在收到broker结果后回调。比较适合不想发送结果影响正常业务逻辑的情况。
- Oneway：Producer提交消息后，无论broker是否正常接收消息都不关心。适合于追求高吞吐、能容忍消息丢失的场景，比如日志收集。

### MQClientInstance启动过程

```java
public void start() throws MQClientException {

        synchronized (this) {
            switch (this.serviceState) {
                case CREATE_JUST:
                    this.serviceState = ServiceState.START_FAILED;
                    // 1、如果NameservAddr为空，尝试从http server获取nameserv的地址
                    if (null == this.clientConfig.getNamesrvAddr()) {
                        this.mQClientAPIImpl.fetchNameServerAddr();
                    }
                    // Start request-response channel
                    // 2、启动MQClientAPIImpl，初始化NettyClient
                    this.mQClientAPIImpl.start();
                    // 3、开启Client的定时任务
                    this.startScheduledTask();
                    // 4、Start pull service,开始处理PullRequest
                    this.pullMessageService.start();
                    // 5、Start rebalance service
                    this.rebalanceService.start();
                    // Start push service
                    //6、启动Client内置的producer
                    this.defaultMQProducer.getDefaultMQProducerImpl().start(false);
                    log.info("the client factory [{}] start OK", this.clientId);
                    this.serviceState = ServiceState.RUNNING;
                    break;
                case RUNNING:
                    break;
                case SHUTDOWN_ALREADY:
                    break;
                case START_FAILED:
                    throw new MQClientException("The Factory object[" + this.getClientId() + "] has been created before, and failed.", null);
                default:
                    break;
            }
        }
    }
```

1、如果producer在初始化的时候没有设置nameserv的地址，则会尝试从一个http server获取nameserv。这个httpserver是可以配置的，这种方式非常适合于有统一配置中心的系统
 3、这里开启的定时任务有以下几个：
 1）获取nameserv地址，就是重复的做第1步，这样就可以动态切换nameserv的地址
 2）从nameserv更新topicRouteInfo，对于producer来说topic的路由信息是最重要的
 3）将缓存的broker信息和最新的topicRouteInfo做对比，清除已经下线的broker
 4）向broker发送心跳

### 消息发送

Producer默认采用SYNC方式提交消息，消息提交给broker收到response后返回。方法是`DefaultMQProducerImpl.send( Message msg)`

```java
/**
     * DEFAULT SYNC -------------------------------------------------------
     */
    public SendResult send(
        Message msg) throws MQClientException, RemotingException, MQBrokerException, InterruptedException {
        return send(msg, this.defaultMQProducer.getSendMsgTimeout());
    }
    public SendResult send(Message msg,
        long timeout) throws MQClientException, RemotingException, MQBrokerException, InterruptedException {
        return this.sendDefaultImpl(msg, CommunicationMode.SYNC, null, timeout);
    }

    private SendResult sendDefaultImpl(
        Message msg,
        final CommunicationMode communicationMode,
        final SendCallback sendCallback,
        final long timeout
    ) throws MQClientException, RemotingException, MQBrokerException, InterruptedException {
        //1、参数检查，消息不能发给系统预留的topic，消息体是否超过最大长度
        this.makeSureStateOK();
        Validators.checkMessage(msg, this.defaultMQProducer);

        final long invokeID = random.nextLong();
        long beginTimestampFirst = System.currentTimeMillis();
        long beginTimestampPrev = beginTimestampFirst;
        long endTimestamp = beginTimestampFirst;
        //2、根据消息的topic，获取该topic的路由信息
        TopicPublishInfo topicPublishInfo = this.tryToFindTopicPublishInfo(msg.getTopic());
        if (topicPublishInfo != null && topicPublishInfo.ok()) {
            boolean callTimeout = false;
            ....
            //3、发送重试次数
            int timesTotal = communicationMode == CommunicationMode.SYNC ? 1 + this.defaultMQProducer.getRetryTimesWhenSendFailed() : 1;
            int times = 0; 
            //用来缓存发送和重试中已经用过的broker
            String[] brokersSent = new String[timesTotal];
            for (; times < timesTotal; times++) {
                String lastBrokerName = null == mq ? null : mq.getBrokerName();
                //4、从所有topic可用queue中选择一个queue
                MessageQueue mqSelected = this.selectOneMessageQueue(topicPublishInfo, lastBrokerName);
                if (mqSelected != null) {//获取Queue成功
                    mq = mqSelected;
                    brokersSent[times] = mq.getBrokerName();
                    try {
                        ...
                        //5、提交消息到mq
                        sendResult = this.sendKernelImpl(msg, mq, communicationMode, sendCallback, topicPublishInfo, timeout - costTime);
                        endTimestamp = System.currentTimeMillis();
                        //6、成功，更新本次调用时间到MQFaultStrategy中
                        this.updateFaultItem(mq.getBrokerName(), endTimestamp - beginTimestampPrev, false);
                        switch (communicationMode) {
                            //异步和ONEWAY调用后就直接返回了
                            case ASYNC:
                                return null;
                            case ONEWAY:
                                return null;
                            //7、如果broker存储失败，判断是否要重试
                            case SYNC:
                                if (sendResult.getSendStatus() != SendStatus.SEND_OK) {
                                    if (this.defaultMQProducer.isRetryAnotherBrokerWhenNotStoreOK()) {
                                        continue;
                                    }
                                }

                                return sendResult;
                            default:
                                break;
                        }
                    // 8、调用接口异常，更新状态到MQFaultStrategy中
                    } catch (RemotingException e) {
                        endTimestamp = System.currentTimeMillis();
                        this.updateFaultItem(mq.getBrokerName(), endTimestamp - beginTimestampPrev, true);
                        ...
                        exception = e;
                        continue;
                    } catch (MQClientException e) {
                        endTimestamp = System.currentTimeMillis();
                        this.updateFaultItem(mq.getBrokerName(), endTimestamp - beginTimestampPrev, true);
                        ...
                        exception = e;
                        continue;
                    } catch (MQBrokerException e) {
                        endTimestamp = System.currentTimeMillis();
                        this.updateFaultItem(mq.getBrokerName(), endTimestamp - beginTimestampPrev, true);
                        ...
                        exception = e;
                        switch (e.getResponseCode()) {
                            case ResponseCode.TOPIC_NOT_EXIST:
                            case ResponseCode.SERVICE_NOT_AVAILABLE:
                            case ResponseCode.SYSTEM_ERROR:
                            case ResponseCode.NO_PERMISSION:
                            case ResponseCode.NO_BUYER_ID:
                            case ResponseCode.NOT_IN_CURRENT_UNIT:
                                continue;
                            default:
                                if (sendResult != null) {
                                    return sendResult;
                                }

                                throw e;
                        }
                    } catch (InterruptedException e) {
                        endTimestamp = System.currentTimeMillis();
                        this.updateFaultItem(mq.getBrokerName(), endTimestamp - beginTimestampPrev, false);
                        ...
                        throw e;
                    }
                } else {
                    break;
                }
            }
            //9、成功则返回结果
            if (sendResult != null) {
                return sendResult;
            }

            ...
            MQClientException mqClientException = new MQClientException(info, exception);
            if (callTimeout) {
                throw new RemotingTooMuchRequestException("sendDefaultImpl call timeout");
            }
            //超过重试次数后，根据不同的错误设置抛出异常类型
            if (exception instanceof MQBrokerException) {
                mqClientException.setResponseCode(((MQBrokerException) exception).getResponseCode());
            } else if (exception instanceof RemotingConnectException) {
                mqClientException.setResponseCode(ClientErrorCode.CONNECT_BROKER_EXCEPTION);
            } else if (exception instanceof RemotingTimeoutException) {
                mqClientException.setResponseCode(ClientErrorCode.ACCESS_BROKER_TIMEOUT);
            } else if (exception instanceof MQClientException) {
                mqClientException.setResponseCode(ClientErrorCode.BROKER_NOT_EXIST_EXCEPTION);
            }

            throw mqClientException;
        }
        ...
    }
```



### 负载均衡

![image-20200322141258521](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200322141258521.png)

```java
    private SendResult sendDefaultImpl(
        Message msg,
        final CommunicationMode communicationMode,
        final SendCallback sendCallback,
        final long timeout
    ) throws MQClientException, RemotingException, MQBrokerException, InterruptedException {
        //1、参数检查，消息不能发给系统预留的topic，消息体是否超过最大长度
        this.makeSureStateOK();
        Validators.checkMessage(msg, this.defaultMQProducer);

        final long invokeID = random.nextLong();
        long beginTimestampFirst = System.currentTimeMillis();
        long beginTimestampPrev = beginTimestampFirst;
        long endTimestamp = beginTimestampFirst;
        //2、根据消息的topic，获取该topic的路由信息
        TopicPublishInfo topicPublishInfo = this.tryToFindTopicPublishInfo(msg.getTopic());
        if (topicPublishInfo != null && topicPublishInfo.ok()) {
            boolean callTimeout = false;
            ....
            //3、发送重试次数
            int timesTotal = communicationMode == CommunicationMode.SYNC ? 1 + this.defaultMQProducer.getRetryTimesWhenSendFailed() : 1;
            int times = 0; 
            //用来缓存发送和重试中已经用过的broker
            String[] brokersSent = new String[timesTotal];
            for (; times < timesTotal; times++) {
                String lastBrokerName = null == mq ? null : mq.getBrokerName();
                //4、从所有topic可用queue中选择一个queue
                MessageQueue mqSelected = this.selectOneMessageQueue(topicPublishInfo, lastBrokerName);
                if (mqSelected != null) {//获取Queue成功
                    mq = mqSelected;
                    brokersSent[times] = mq.getBrokerName();
                    try {
                        ...
                        //5、提交消息到mq
                        sendResult = this.sendKernelImpl(msg, mq, communicationMode, sendCallback, topicPublishInfo, timeout - costTime);
                        endTimestamp = System.currentTimeMillis();
                        //6、成功，更新本次调用时间到MQFaultStrategy中
                        this.updateFaultItem(mq.getBrokerName(), endTimestamp - beginTimestampPrev, false);
                        switch (communicationMode) {
                            //异步和ONEWAY调用后就直接返回了
                            case ASYNC:
                                return null;
                            case ONEWAY:
                                return null;
                            //7、如果broker存储失败，判断是否要重试
                            case SYNC:
                                if (sendResult.getSendStatus() != SendStatus.SEND_OK) {
                                    if (this.defaultMQProducer.isRetryAnotherBrokerWhenNotStoreOK()) {
                                        continue;
                                    }
                                }

                                return sendResult;
                            default:
                                break;
                        }
                    // 8、调用接口异常，更新状态到MQFaultStrategy中
                    } catch (RemotingException e) {
                        endTimestamp = System.currentTimeMillis();
                        this.updateFaultItem(mq.getBrokerName(), endTimestamp - beginTimestampPrev, true);
                        ...
                        exception = e;
                        continue;
                    } catch (MQClientException e) {
                        endTimestamp = System.currentTimeMillis();
                        this.updateFaultItem(mq.getBrokerName(), endTimestamp - beginTimestampPrev, true);
                        ...
                        exception = e;
                        continue;
                    } catch (MQBrokerException e) {
                        endTimestamp = System.currentTimeMillis();
                        this.updateFaultItem(mq.getBrokerName(), endTimestamp - beginTimestampPrev, true);
                        ...
                        exception = e;
                        switch (e.getResponseCode()) {
                            case ResponseCode.TOPIC_NOT_EXIST:
                            case ResponseCode.SERVICE_NOT_AVAILABLE:
                            case ResponseCode.SYSTEM_ERROR:
                            case ResponseCode.NO_PERMISSION:
                            case ResponseCode.NO_BUYER_ID:
                            case ResponseCode.NOT_IN_CURRENT_UNIT:
                                continue;
                            default:
                                if (sendResult != null) {
                                    return sendResult;
                                }

                                throw e;
                        }
                    } catch (InterruptedException e) {
                        endTimestamp = System.currentTimeMillis();
                        this.updateFaultItem(mq.getBrokerName(), endTimestamp - beginTimestampPrev, false);
                        ...
                        throw e;
                    }
                } else {
                    break;
                }
            }
            //9、成功则返回结果
            if (sendResult != null) {
                return sendResult;
            }

            ...
            MQClientException mqClientException = new MQClientException(info, exception);
            if (callTimeout) {
                throw new RemotingTooMuchRequestException("sendDefaultImpl call timeout");
            }
            //超过重试次数后，根据不同的错误设置抛出异常类型
            if (exception instanceof MQBrokerException) {
                mqClientException.setResponseCode(((MQBrokerException) exception).getResponseCode());
            } else if (exception instanceof RemotingConnectException) {
                mqClientException.setResponseCode(ClientErrorCode.CONNECT_BROKER_EXCEPTION);
            } else if (exception instanceof RemotingTimeoutException) {
                mqClientException.setResponseCode(ClientErrorCode.ACCESS_BROKER_TIMEOUT);
            } else if (exception instanceof MQClientException) {
                mqClientException.setResponseCode(ClientErrorCode.BROKER_NOT_EXIST_EXCEPTION);
            }

            throw mqClientException;
        }
        ...
    }
```

如果Producer发送消息失败，会自动重试，重试的策略：

1. 重试次数 < retryTimesWhenSendFailed（可配置）
2. 总的耗时（包含重试n次的耗时） < sendMsgTimeout（发送消息时传入的参数）
3. 同时满足上面两个条件后，Producer会选择另外一个队列发送消息

### 选择消息队列

轮询

selectOneMessageQueue

1 ) sendLatencyFaultEnable=false，默认不启用Broker故障延迟机制

2 ) sendLatencyFaultEnable=true，启用Broker故障延迟机制

`RocketMQ` 中将生产者端剔除故障机器的机制称之为 `Broker` 的故障延迟机制，一旦发现发送到某个 `Broker` 机器失败，则暂时将其剔除，优先选择其他 `Broker` 重试

### 生产成功的标志

 brokerRole有两种ASYNC_MASTER || SYNC_MASTER

![image-20200401145218215](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200401145218215.png)

### 自动创建主题

![image-20200407164958084](https://github.com/garydai/garydai.github.com/raw/master/_posts/image-20200407164958084.png)

提示：消息发送者在到默认路由信息时，其队列数量，会选择DefaultMQProducer#defaultTopicQueueNums与Nameserver返回的的队列数8取最小值，DefaultMQProducer#defaultTopicQueueNums默认值为4，故自动创建的主题，其队列数量默认为4。

因为开启了自动创建路由信息，消息发送者根据Topic去NameServer无法得到路由信息，但接下来根据默认Topic从NameServer是能拿到路由信息(在每个Broker中，存在8个队列)，因为两个Broker在启动时都会向NameServer汇报路由信息。此时消息发送者缓存的路由信息是2个Broker，每个Broker默认4个队列



**rocketmq在发送消息时，会先去获取topic的路由信息，如果topic是第一次发送消息，由于nameserver没有topic的路由信息，所以会再次以“TBW102”这个默认topic获取路由信息，假设broker都开启了自动创建开关，那么此时会获取所有broker的路由信息，消息的发送会根据负载算法选择其中一台Broker发送消息，消息到达broker后，发现本地没有该topic，会在创建该topic的信息塞进本地缓存中，同时会将topic路由信息注册到nameserver中，那么这样就会造成一个后果：以后所有该topic的消息，都将发送到这台broker上，如果该topic消息量非常大，会造成某个broker上负载过大，这样消息的存储就达不到负载均衡的目的了。**



## 分片

topic根据broker分片，在同一个broker里分片成多个queue

比kakfa多分了一层

![image-20200322114127511](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200322114127511.png)

## 集群

### broker

rocketmq是通过多个master实现写入容灾，通过主从实现读取容灾

这一组Broker的Master挂了，但是这组中的Slave可以继续提供读的服务，直至把未消费完的消息全部读完；这一组的Master挂了，写的服务会找另一组的Master继续写

![image-20200402095452874](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200402095452874.png)

其中broker的角色主要有两种：Master和Slave。作为Master的副本，Slave会从Master复制消息，保持同步。在RocketMQ中，消息生产者Producer只会往Master中写入消息。一般情况下，消息消费者Consumer也只会从Master中拉取消息，但当Master不可用或者拉取堆积消息时会转向Slave中进行拉取。

RocketMQ中增加从节点有如下好处：

- 数据备份

特别是在**主从同步复制**的情况下，保证了两/多台机器上的数据冗余，一定程度上保证了Master出现不可恢复的故障以后，数据不丢失。

- 高可用性

即使Master掉线，Consumer会自动重连到对应的Slave机器，不会出现消费停滞的情况。（注：若此时Topic存在在多个Master上，一个Master掉线，Producer也会发送其余Master上，保证消息的正常发送，这里也体现了RocketMQ的高可用性）

- 提高性能

主要表现为可分担Master读的压力，当从Master拉取消息，拉取消息的最大物理偏移与本地存储的最大物理偏移的差值超过一定值（默认是物理内存的40%），会转向Slave(默认brokerId=1)进行读取，减轻了Master压力，提高性能

![image-20200402123417876](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200402123417876.png)

### 同步commitlog

![image-20200402124441966](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200402124441966.png)

### 主备Broker异步同步流程图

![image-20200402181546459](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200402181546459.png)

### 主备Broker同步双写流程图

![image-20200402181604287](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200402181604287.png)

## 问题

1. 如何算消息生产成功？sync、async
2. messageQueue分配规则

## 参考

https://blog.csdn.net/qq_27641935/article/details/86539980

https://www.cnblogs.com/duanxz/p/3509074.html

http://www.jinrongtong5.com/article/53

https://blog.csdn.net/meilong_whpu/article/details/76922456

RocketMQ技术内幕

https://www.zhihu.com/question/30195969

https://tinylcy.me/2019/the-design-of-rocketmq-message-storage-system/