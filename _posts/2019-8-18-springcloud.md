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



```java
/**
 * Annotation to mark a RestTemplate bean to be configured to use a LoadBalancerClient
 * @author Spencer Gibb
 */
@Target({ ElementType.FIELD, ElementType.PARAMETER, ElementType.METHOD })
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Inherited
@Qualifier
public @interface LoadBalanced {
}
```

```java
@Configuration
@ConditionalOnClass(RestTemplate.class)
@ConditionalOnBean(LoadBalancerClient.class)
@EnableConfigurationProperties(LoadBalancerRetryProperties.class)
public class LoadBalancerAutoConfiguration {

  	// 收集被loadBalanced标记的restTemplate
   @LoadBalanced 
   @Autowired(required = false)
   private List<RestTemplate> restTemplates = Collections.emptyList();

   @Bean
   public SmartInitializingSingleton loadBalancedRestTemplateInitializer(
         final List<RestTemplateCustomizer> customizers) {
      return new SmartInitializingSingleton() {
         @Override
         public void afterSingletonsInstantiated() {
            for (RestTemplate restTemplate : LoadBalancerAutoConfiguration.this.restTemplates) {
               for (RestTemplateCustomizer customizer : customizers) {
                  customizer.customize(restTemplate);
               }
            }
         }
      };
   }
  
  
  @Configuration(proxyBeanMethods = false)
	@ConditionalOnMissingClass("org.springframework.retry.support.RetryTemplate")
	static class LoadBalancerInterceptorConfig {

		@Bean
		public LoadBalancerInterceptor ribbonInterceptor(
				LoadBalancerClient loadBalancerClient,
				LoadBalancerRequestFactory requestFactory) {
			return new LoadBalancerInterceptor(loadBalancerClient, requestFactory);
		}

		@Bean
		@ConditionalOnMissingBean
		public RestTemplateCustomizer restTemplateCustomizer(
				final LoadBalancerInterceptor loadBalancerInterceptor) {
			return restTemplate -> {
				List<ClientHttpRequestInterceptor> list = new ArrayList<>(
						restTemplate.getInterceptors());
				list.add(loadBalancerInterceptor);
				restTemplate.setInterceptors(list);
			};
		}

	}
  
}
```

org.springframework.cloud.netflix.ribbon.RibbonAutoConfiguration

```java
	@Bean
	@ConditionalOnMissingBean(LoadBalancerClient.class)
	public LoadBalancerClient loadBalancerClient() {
		return new RibbonLoadBalancerClient(springClientFactory());
	}
```



流程：

1. 拦截restremplate
2. 根据server name获取负载均衡器（会创建spring子容器）
3. 负载均衡器获取eureka服务信息（两个定时任务）
4. 根据负载均衡器算法调用服务



DynamicServerListLoadBalancer

实现：

1. 去eureka客户端缓存获取服务信息
2. 定时刷新服务信息，30s（com.netflix.loadbalancer.PollingServerListUpdater）

``` java
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

### 配置隔离

## feign

![image-20210828100600154](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210828100600154.png)



类似mabtis的dao，代理http请求

```java
@EnableFeignClients
```

```
@Import(FeignClientsRegistrar.class)
```



org.springframework.cloud.openfeign.FeignClientsRegistrar#registerBeanDefinitions

```java
	@Override
	public void registerBeanDefinitions(AnnotationMetadata metadata,
			BeanDefinitionRegistry registry) {
		registerDefaultConfiguration(metadata, registry);
    // 扫描@EnableFeignClients制定的类，并对@feignclient标注的类生成bean definition并注册到ioc容器
		registerFeignClients(metadata, registry);
	}
```



org.springframework.cloud.openfeign.FeignClientsRegistrar#registerDefaultConfiguration

```java
private void registerDefaultConfiguration(AnnotationMetadata metadata,BeanDefinitionRegistry registry) {
   Map<String, Object> defaultAttrs = metadata
         .getAnnotationAttributes(EnableFeignClients.class.getName(), true);

   if (defaultAttrs != null && defaultAttrs.containsKey("defaultConfiguration")) {
      String name;
      if (metadata.hasEnclosingClass()) {
         name = "default." + metadata.getEnclosingClassName();
      }
      else {
         name = "default." + metadata.getClassName();
      }
      registerClientConfiguration(registry, name,
            defaultAttrs.get("defaultConfiguration"));
   }
}
private void registerClientConfiguration(BeanDefinitionRegistry registry, Object name,Object configuration) {
	BeanDefinitionBuilder builder = BeanDefinitionBuilder.genericBeanDefinition(FeignClientSpecification.class);
	builder.addConstructorArgValue(name);
	builder.addConstructorArgValue(configuration);
	registry.registerBeanDefinition(name + "." + FeignClientSpecification.class.getSimpleName(),builder.getBeanDefinition());
}


```



#### 注册FeignClientSpecification

NamedContextFactory springboot的子容器

```java
class FeignClientSpecification implements NamedContextFactory.Specification {
}
```





#### 注册FeignClient

org.springframework.cloud.openfeign.FeignClientsRegistrar#registerFeignClient

beanClass=class org.springframework.cloud.openfeign.FeignClientFactoryBean



```java
//attributes  @FeignClient中读取的配置信息
private void registerFeignClient(BeanDefinitionRegistry registry, AnnotationMetadata annotationMetadata, Map<String, Object> attributes) {
   String className = annotationMetadata.getClassName();
   //重点！！！BeanDefinition类型为FeignClientFactoryBean
   BeanDefinitionBuilder definition = BeanDefinitionBuilder.genericBeanDefinition(FeignClientFactoryBean.class);
   validate(attributes);
   definition.addPropertyValue("url", getUrl(attributes));
   definition.addPropertyValue("path", getPath(attributes));
   String name = getName(attributes);
   definition.addPropertyValue("name", name);
   String contextId = getContextId(attributes);
   definition.addPropertyValue("contextId", contextId);
   //type 设置的FactoryBean 返回的 类型
   definition.addPropertyValue("type", className);
   definition.addPropertyValue("decode404", attributes.get("decode404"));
   definition.addPropertyValue("fallback", attributes.get("fallback"));
   definition.addPropertyValue("fallbackFactory", attributes.get("fallbackFactory"));
   definition.setAutowireMode(AbstractBeanDefinition.AUTOWIRE_BY_TYPE);

   String alias = contextId + "FeignClient";
   AbstractBeanDefinition beanDefinition = definition.getBeanDefinition();
   beanDefinition.setAttribute(FactoryBean.OBJECT_TYPE_ATTRIBUTE, className);

   // has a default, won't be null
   boolean primary = (Boolean) attributes.get("primary");

   beanDefinition.setPrimary(primary);

   String qualifier = getQualifier(attributes);
   if (StringUtils.hasText(qualifier)) {
      alias = qualifier;
   }
   BeanDefinitionHolder holder = new BeanDefinitionHolder(beanDefinition, className,
         new String[] { alias });
   BeanDefinitionReaderUtils.registerBeanDefinition(holder, registry);
}


```

org.springframework.cloud.openfeign.FeignClientFactoryBean#getObject

```java
@Override
public Object getObject() throws Exception {
   return getTarget();
}

/**
 * @param <T> the target type of the Feign client
 * @return a {@link Feign} client created with the specified data and the context
 * information
 */
<T> T getTarget() {
   // context 工厂FeignContext extends NamedContextFactory<FeignClientSpecification> 
   FeignContext context = applicationContext.getBean(FeignContext.class);
   //每个feignclient创建一个子容器applicationcontext

   if (!StringUtils.hasText(url)) {
      if (!name.startsWith("http")) {
         url = "http://" + name;
      }
      else {
         url = name;
      }
      url += cleanPath();
      // 采用负载均衡客户端，由FeignLoadBalancerAutoConfiguration配置
      return (T) loadBalance(builder, context,
            new HardCodedTarget<>(type, name, url));
   }
   if (StringUtils.hasText(url) && !url.startsWith("http")) {
      url = "http://" + url;
   }
   String url = this.url + cleanPath();
   Client client = getOptional(context, Client.class);
   if (client != null) {
      if (client instanceof LoadBalancerFeignClient) {
         // not load balancing because we have a url,
         // but ribbon is on the classpath, so unwrap
         // 不采用负载均衡
         client = ((LoadBalancerFeignClient) client).getDelegate();
      }
      if (client instanceof FeignBlockingLoadBalancerClient) {
         // not load balancing because we have a url,
         // but Spring Cloud LoadBalancer is on the classpath, so unwrap
        // 不采用负载均衡
         client = ((FeignBlockingLoadBalancerClient) client).getDelegate();
      }
      builder.client(client);
   }
   Targeter targeter = get(context, Targeter.class);
   return (T) targeter.target(this, builder, context,
         new HardCodedTarget<>(type, name, url));
}
```

```java
protected Feign.Builder feign(FeignContext context) {
   FeignLoggerFactory loggerFactory = get(context, FeignLoggerFactory.class);
   Logger logger = loggerFactory.create(type);

   // @formatter:off
   Feign.Builder builder = get(context, Feign.Builder.class)
         // required values
         .logger(logger)
         .encoder(get(context, Encoder.class))
         .decoder(get(context, Decoder.class))
         .contract(get(context, Contract.class));
   // @formatter:on

   configureFeign(context, builder);

   return builder;
}

protected <T> T get(FeignContext context, Class<T> type) {
    // 从容器包括父容器里找Feign.Builder.class
		T instance = context.getInstance(contextId, type);
		if (instance == null) {
			throw new IllegalStateException(
					"No bean found of type " + type + " for " + contextId);
		}
		return instance;
	}
```

```java
@Import({ HttpClientFeignLoadBalancerConfiguration.class,
      OkHttpFeignLoadBalancerConfiguration.class,
      DefaultFeignLoadBalancerConfiguration.class })
public class FeignLoadBalancerAutoConfiguration {

}

```

```java

@Configuration(proxyBeanMethods = false)
@ConditionalOnClass(OkHttpClient.class)
@ConditionalOnProperty("feign.okhttp.enabled")
@ConditionalOnBean(BlockingLoadBalancerClient.class)
@Import(OkHttpFeignConfiguration.class)
class OkHttpFeignLoadBalancerConfiguration {

   @Bean
   @ConditionalOnMissingBean
   @Conditional(OnRetryNotEnabledCondition.class)
   public Client feignClient(okhttp3.OkHttpClient okHttpClient,BlockingLoadBalancerClient loadBalancerClient) {
      OkHttpClient delegate = new OkHttpClient(okHttpClient);
      //装饰为 FeignBlockingLoadBalancerClient 带有负载均衡功能
      return new FeignBlockingLoadBalancerClient(delegate, loadBalancerClient);
   }

   @Bean
   @ConditionalOnMissingBean
   @ConditionalOnClass(name = "org.springframework.retry.support.RetryTemplate")
   @ConditionalOnBean(LoadBalancedRetryFactory.class)
   @ConditionalOnProperty(value = "spring.cloud.loadbalancer.retry.enabled",
         havingValue = "true", matchIfMissing = true)
   public Client feignRetryClient(BlockingLoadBalancerClient loadBalancerClient,
         okhttp3.OkHttpClient okHttpClient,
         List<LoadBalancedRetryFactory> loadBalancedRetryFactories) {
      AnnotationAwareOrderComparator.sort(loadBalancedRetryFactories);
      OkHttpClient delegate = new OkHttpClient(okHttpClient);
      return new RetryableFeignBlockingLoadBalancerClient(delegate, loadBalancerClient,
            loadBalancedRetryFactories.get(0));
   }

}


```



每个feignclient创建一个AnnotationConfigApplicationContext

```java
protected AnnotationConfigApplicationContext createContext(String name) {
   AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext();
   // 注册@feignclient指定的配置类
   if (this.configurations.containsKey(name)) {
      for (Class<?> configuration : this.configurations.get(name)
            .getConfiguration()) {
         context.register(configuration);
      }
   }
  
  // 注册缺省配置default开头的配置类，由@enableFeignclient指定的配置类
   for (Map.Entry<String, C> entry : this.configurations.entrySet()) {
      if (entry.getKey().startsWith("default.")) {
         for (Class<?> configuration : entry.getValue().getConfiguration()) {
            context.register(configuration);
         }
      }
   }
  // 注册org.springframework.cloud.openfeign.FeignClientsConfiguration和PropertyPlaceholderAutoConfiguration
   context.register(PropertyPlaceholderAutoConfiguration.class,
         this.defaultConfigType);
  
   context.getEnvironment().getPropertySources().addFirst(new MapPropertySource(
         this.propertySourceName,
         Collections.<String, Object>singletonMap(this.propertyName, name)));
   if (this.parent != null) {
      // Uses Environment from parent as well as beans
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

feign默认使用ribbon负载均衡器

org/springframework/cloud/spring-cloud-openfeign-core/2.2.6.RELEASE/spring-cloud-openfeign-core-2.2.6.RELEASE.jar!/META-INF/spring.factories

```java
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
org.springframework.cloud.openfeign.ribbon.FeignRibbonClientAutoConfiguration,\
org.springframework.cloud.openfeign.hateoas.FeignHalAutoConfiguration,\
org.springframework.cloud.openfeign.FeignAutoConfiguration,\
org.springframework.cloud.openfeign.encoding.FeignAcceptGzipEncodingAutoConfiguration,\
org.springframework.cloud.openfeign.encoding.FeignContentGzipEncodingAutoConfiguration,\
org.springframework.cloud.openfeign.loadbalancer.FeignLoadBalancerAutoConfiguration
```

```java
@ConditionalOnClass({ ILoadBalancer.class, Feign.class })
@ConditionalOnProperty(value = "spring.cloud.loadbalancer.ribbon.enabled",
      matchIfMissing = true)
@Configuration(proxyBeanMethods = false)
@AutoConfigureBefore(FeignAutoConfiguration.class)
@EnableConfigurationProperties({ FeignHttpClientProperties.class })
// Order is important here, last should be the default, first should be optional
// see
// https://github.com/spring-cloud/spring-cloud-netflix/issues/2086#issuecomment-316281653
// 默认导入HttpClientFeignLoadBalancedConfiguration
@Import({ HttpClientFeignLoadBalancedConfiguration.class,
      OkHttpFeignLoadBalancedConfiguration.class,
      DefaultFeignLoadBalancedConfiguration.class })
public class FeignRibbonClientAutoConfiguration {

   @Bean
   @Primary
   @ConditionalOnMissingBean
   @ConditionalOnMissingClass("org.springframework.retry.support.RetryTemplate")
   public CachingSpringLoadBalancerFactory cachingLBClientFactory(
         SpringClientFactory factory) {
      return new CachingSpringLoadBalancerFactory(factory);
   }

   @Bean
   @Primary
   @ConditionalOnMissingBean
   @ConditionalOnClass(name = "org.springframework.retry.support.RetryTemplate")
   public CachingSpringLoadBalancerFactory retryabeCachingLBClientFactory(
         SpringClientFactory factory, LoadBalancedRetryFactory retryFactory) {
      return new CachingSpringLoadBalancerFactory(factory, retryFactory);
   }

   @Bean
   @ConditionalOnMissingBean
   public Request.Options feignRequestOptions() {
      return LoadBalancerFeignClient.DEFAULT_OPTIONS;
   }

}
```

```java
@Configuration(proxyBeanMethods = false)
@ConditionalOnClass(ApacheHttpClient.class)
@ConditionalOnProperty(value = "feign.httpclient.enabled", matchIfMissing = true)
@Import(HttpClientFeignConfiguration.class)
class HttpClientFeignLoadBalancedConfiguration {

   @Bean
   @ConditionalOnMissingBean(Client.class)
   public Client feignClient(CachingSpringLoadBalancerFactory cachingFactory,
         SpringClientFactory clientFactory, HttpClient httpClient) {
      ApacheHttpClient delegate = new ApacheHttpClient(httpClient);
      return new LoadBalancerFeignClient(delegate, cachingFactory, clientFactory);
   }

}
```

org.springframework.cloud.openfeign.ribbon.LoadBalancerFeignClient#execute

```java
@Override
public Response execute(Request request, Request.Options options) throws IOException {
   try {
      URI asUri = URI.create(request.url());
      String clientName = asUri.getHost();
      URI uriWithoutHost = cleanUrl(request.url(), clientName);
      FeignLoadBalancer.RibbonRequest ribbonRequest = new FeignLoadBalancer.RibbonRequest(
            this.delegate, request, uriWithoutHost);

      IClientConfig requestConfig = getClientConfig(options, clientName);
      return lbClient(clientName)
            .executeWithLoadBalancer(ribbonRequest, requestConfig).toResponse();
   }
   catch (ClientException e) {
      IOException io = findIOException(e);
      if (io != null) {
         throw io;
      }
      throw new RuntimeException(e);
   }
}
```



https://juejin.cn/post/6976557085571940366

### 配置隔离

## hystrix 熔断器

方法降级、超时监听、服务熔断、服务限流

![image-20210826141613514](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210826141613514.png)



org.springframework.cloud.openfeign.FeignClientsConfiguration.HystrixFeignConfiguration

```java
// FeignClientsConfiguration.java
@Configuration
@ConditionalOnClass({ HystrixCommand.class, HystrixFeign.class })
protected static class HystrixFeignConfiguration {
   @Bean
   @Scope("prototype")
   @ConditionalOnMissingBean
   @ConditionalOnProperty(name = "feign.hystrix.enabled", matchIfMissing = false)
   public Feign.Builder feignHystrixBuilder() {
      return HystrixFeign.builder();
   }
}
```

![image-20210826160841546](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210826160841546.png)

http://www.saily.top/2020/04/19/springcloud/hystrix05/

## zuul 网关

路由、过滤、容错与回退、集群、高可用
## config 分布式配置

　1.ConfigServer利用了SpringCloud引导机制，当主程序启动时，通过PropertySourceLocator的方法把相关配置读到当前的Environment中，同时提供了EnvironmentController使外界能够根据不同的请求获取不同格式的配置结果，由于是引导程序是核心，因此务必使用bootstrap.yml(properties)进行配置操作。

　　2.SpringCloud的客户端同样利用引导，通过实现PropertySourceLocator接口在程序启动前利用RestTemplate访问ConfigServer获取到配置并加载到当前Environment中

https://www.cnblogs.com/niechen/p/9068479.html

## sleuth 分布式链路跟踪 + zipkin 可视化

![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/springcloud.png)

