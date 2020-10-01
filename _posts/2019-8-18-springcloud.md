---
date: 2019-8-18
layout: default

title: spring cloud

---

# spring cloud
## eureka
服务注册

ap集群
## ribbon
客户端负载均衡
![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/ribbon.png)

原理就是：将spring的restTemplate对象添加拦截器，restTemplate.setInterceptors()

loadBalancerInterceptor



流程：

1. 拦截restremplate
2. 根据server name获取负载均衡器（会创建spring子容器）
3. 负载均衡器获取eureka服务信息（两个定时任务）
4. 根据负载均衡器算法调用服务



DynamicServerListLoadBalancer

实现：

1. 去eureka客户端缓存获取服务信息
2. 定时刷新服务信息，30s（com.netflix.loadbalancer.PollingServerListUpdater）

```
 scheduledFuture = getRefreshExecutor().scheduleWithFixedDelay(
                    wrapperRunnable,
                    initialDelayMs,
                    refreshIntervalMs,
                    TimeUnit.MILLISECONDS
            );
```



3. ping 服务是否存活，10s(com.netflix.loadbalancer.BaseLoadBalancer#setupPingTask)

默认是不会ping，DumyPing

```java
lbTimer = new ShutdownEnabledTimer("NFLoadBalancer-PingTimer-" + name,
        true);
lbTimer.schedule(new PingTask(), 0, pingIntervalSeconds * 1000);
```





org.springframework.cloud.netflix.ribbon.RibbonLoadBalancerClient#execute(java.lang.String, org.springframework.cloud.client.loadbalancer.LoadBalancerRequest<T>, java.lang.Object)

```java
public <T> T execute(String serviceId, LoadBalancerRequest<T> request, Object hint) throws IOException {
        // com.netflix.loadbalancer.DynamicServerListLoadBalancer
        ILoadBalancer loadBalancer = this.getLoadBalancer(serviceId);
        Server server = this.getServer(loadBalancer, hint);
        if (server == null) {
            throw new IllegalStateException("No instances available for " + serviceId);
        } else {
            RibbonLoadBalancerClient.RibbonServer ribbonServer = new RibbonLoadBalancerClient.RibbonServer(serviceId, server, this.isSecure(server, serviceId), this.serverIntrospector(serviceId).getMetadata(server));
            return this.execute(serviceId, (ServiceInstance)ribbonServer, (LoadBalancerRequest)request);
        }
    }
```



每个服务有各自独立的spring子上下文

org.springframework.cloud.context.named.NamedContextFactory#getInstance(java.lang.String, java.lang.Class<T>)

```java
public <T> T getInstance(String name, Class<T> type) {
   AnnotationConfigApplicationContext context = getContext(name);
   if (BeanFactoryUtils.beanNamesForTypeIncludingAncestors(context,
         type).length > 0) {
      return context.getBean(type);
   }
   return null;
}
```

创建上下文

org.springframework.cloud.context.named.NamedContextFactory#createContext

```java
protected AnnotationConfigApplicationContext createContext(String name) {
   AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext();
   // 注册配置类
   if (this.configurations.containsKey(name)) {
      for (Class<?> configuration : this.configurations.get(name)
            .getConfiguration()) {
         context.register(configuration);
      }
   }
   for (Map.Entry<String, C> entry : this.configurations.entrySet()) {
      if (entry.getKey().startsWith("default.")) {
         for (Class<?> configuration : entry.getValue().getConfiguration()) {
            context.register(configuration);
         }
      }
   }
   context.register(PropertyPlaceholderAutoConfiguration.class,
         this.defaultConfigType);
   context.getEnvironment().getPropertySources().addFirst(new MapPropertySource(
         this.propertySourceName,
         Collections.<String, Object>singletonMap(this.propertyName, name)));
   if (this.parent != null) {
      // Uses Environment from parent as well as beans
      // 设置父容器
      context.setParent(this.parent);
      // jdk11 issue
      // https://github.com/spring-cloud/spring-cloud-netflix/issues/3101
      context.setClassLoader(this.parent.getClassLoader());
   }
   context.setDisplayName(generateDisplayName(name));
   context.refresh();
   return context;
}
```



主要的类DynamicServerListLoadBalancer

```java
public DynamicServerListLoadBalancer(IClientConfig clientConfig, IRule rule, IPing ping,
                                     ServerList<T> serverList, ServerListFilter<T> filter,
                                     ServerListUpdater serverListUpdater) {
    super(clientConfig, rule, ping);
    this.serverListImpl = serverList;
    this.filter = filter;
    this.serverListUpdater = serverListUpdater;
    if (filter instanceof AbstractServerListFilter) {
        ((AbstractServerListFilter) filter).setLoadBalancerStats(getLoadBalancerStats());
    }
    restOfInit(clientConfig);
}
```

```java
void restOfInit(IClientConfig clientConfig) {
    boolean primeConnection = this.isEnablePrimingConnections();
    // turn this off to avoid duplicated asynchronous priming done in BaseLoadBalancer.setServerList()
    this.setEnablePrimingConnections(false);
    enableAndInitLearnNewServersFeature();
		
  	// 从eureka client取server
    updateListOfServers();
    if (primeConnection && this.getPrimeConnections() != null) {
        this.getPrimeConnections()
                .primeConnections(getReachableServers());
    }
    this.setEnablePrimingConnections(primeConnection);
    LOGGER.info("DynamicServerListLoadBalancer for client {} initialized: {}", clientConfig.getClientName(), this.toString());
}
```

## feign

类似mabtis的dao，代理http请求

```java
@EnableFeignClients
```

```
@Import(FeignClientsRegistrar.class)
```



## hystrix 熔断器

方法降级、超时监听、服务熔断、服务限流
## zuul 网关
路由、过滤、容错与回退、集群、高可用
## config 分布式配置
## sleuth 分布式链路跟踪 + zipkin 可视化

![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/springcloud.png)


