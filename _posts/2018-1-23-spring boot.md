---
date: 2018-1-23
layout: default

title: spring boot

---

# spring boot

SpringBoot 中运用了大量的 Spring 注解，其注解大致分为这几类：

1. 配置注解：@Configuration、@ComponentScan、@Import、@Conditional、@Bean
2. 模式注解：@Componnt、@Repository、@Service、@Controller
3. @Enable 模块注解：@EnableWebMvc、@EnableTransactionManagement、@EnableWebFlux

配置注解都在 Spring 的 ConfigurationClassParser#doProcessConfigurationClass 方法中进行处理

## spring
DI（依赖注入IOC）

AOP（面向切面编程）

把有一些类注解，实例一次，放入ioc容器

通过autowired等注解，从ioc容器里拿实例

## spring boot

内置web server

创建一个基于spring的应用简单

自动配置

零xml配置

​	src\main\resources

src\main\resources\config

## 程序开始

SpringApplication.run（），进行自动配置

### SpringApplication构造函数

org.springframework.boot.SpringApplication#SpringApplication(org.springframework.core.io.ResourceLoader, java.lang.Class<?>...)

```java
public SpringApplication(ResourceLoader resourceLoader, Class<?>... primarySources) {
		this.resourceLoader = resourceLoader;
		Assert.notNull(primarySources, "PrimarySources must not be null");
		this.primarySources = new LinkedHashSet<>(Arrays.asList(primarySources));
		this.webApplicationType = deduceWebApplicationType();
    // 从spring.factories找到org.springframework.context.ApplicationContextInitializer实现类并实例化
		setInitializers((Collection) getSpringFactoriesInstances(
				ApplicationContextInitializer.class));
    // 从spring.factories找到org.springframework.context.ApplicationListener实现类并实例化
		setListeners((Collection) getSpringFactoriesInstances(ApplicationListener.class));
    // 根据调用栈，拿到main启动类 new RuntimeException().getStackTrace() 
		this.mainApplicationClass = deduceMainApplicationClass();
	}
```

```java
private <T> Collection<T> getSpringFactoriesInstances(Class<T> type,
      Class<?>[] parameterTypes, Object... args) {
   ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
   // Use names and ensure unique to protect against duplicates
   // 从spring.factories找到type实现类全限定名
   Set<String> names = new LinkedHashSet<>(
         SpringFactoriesLoader.loadFactoryNames(type, classLoader));
   // 实例化
   List<T> instances = createSpringFactoriesInstances(type, parameterTypes,
         classLoader, args, names);
   AnnotationAwareOrderComparator.sort(instances);
   return instances;
```

```java
private <T> List<T> createSpringFactoriesInstances(Class<T> type,
      Class<?>[] parameterTypes, ClassLoader classLoader, Object[] args,
      Set<String> names) {
   List<T> instances = new ArrayList<>(names.size());
   for (String name : names) {
      try {
         Class<?> instanceClass = ClassUtils.forName(name, classLoader);
         Assert.isAssignable(type, instanceClass);
         Constructor<?> constructor = instanceClass
               .getDeclaredConstructor(parameterTypes);
         // 实例化
         T instance = (T) BeanUtils.instantiateClass(constructor, args);
         instances.add(instance);
      }
      catch (Throwable ex) {
         throw new IllegalArgumentException(
               "Cannot instantiate " + type + " : " + name, ex);
      }
   }
   return instances;
}
```

```java
springboot autoconfiguration的meta-inf的spring.factories文件
# Initializers
org.springframework.context.ApplicationContextInitializer=\
org.springframework.boot.autoconfigure.SharedMetadataReaderFactoryContextInitializer,\
org.springframework.boot.autoconfigure.logging.ConditionEvaluationReportLoggingListener

# Application Listeners
org.springframework.context.ApplicationListener=\
org.springframework.boot.autoconfigure.BackgroundPreinitializer


 0 = "org.springframework.boot.context.ConfigurationWarningsApplicationContextInitializer"
 1 = "org.springframework.boot.context.ContextIdApplicationContextInitializer"
 2 = "org.springframework.boot.context.config.DelegatingApplicationContextInitializer"
 3 = "org.springframework.boot.web.context.ServerPortInfoApplicationContextInitializer"
 4 = "org.springframework.boot.autoconfigure.SharedMetadataReaderFactoryContextInitializer"
 5 = "org.springframework.boot.autoconfigure.logging.ConditionEvaluationReportLoggingListener"

```

#### run函数

```java
public ConfigurableApplicationContext run(String... args) {
   StopWatch stopWatch = new StopWatch();
   stopWatch.start();
   ConfigurableApplicationContext context = null;
   Collection<SpringBootExceptionReporter> exceptionReporters = new ArrayList<>();
   configureHeadlessProperty();
   SpringApplicationRunListeners listeners = getRunListeners(args);
   listeners.starting();
   try {
      ApplicationArguments applicationArguments = new DefaultApplicationArguments(
            args);
     // 准备环境
      ConfigurableEnvironment environment = prepareEnvironment(listeners,
            applicationArguments);
      configureIgnoreBeanInfo(environment);
      Banner printedBanner = printBanner(environment);
      // 创建spring容器，和web服务器
      context = createApplicationContext();
     
      exceptionReporters = getSpringFactoriesInstances(
            SpringBootExceptionReporter.class,
            new Class[] { ConfigurableApplicationContext.class }, context);
     
      prepareContext(context, environment, listeners, applicationArguments,
            printedBanner);
     
      refreshContext(context);
      afterRefresh(context, applicationArguments);
      stopWatch.stop();
      if (this.logStartupInfo) {
         new StartupInfoLogger(this.mainApplicationClass)
               .logStarted(getApplicationLog(), stopWatch);
      }
      listeners.started(context);
      callRunners(context, applicationArguments);
   }
   catch (Throwable ex) {
      handleRunFailure(context, ex, exceptionReporters, listeners);
      throw new IllegalStateException(ex);
   }

   try {
      listeners.running(context);
   }
   catch (Throwable ex) {
      handleRunFailure(context, ex, exceptionReporters, null);
      throw new IllegalStateException(ex);
   }
   return context;
}
```

```java
private ConfigurableEnvironment prepareEnvironment(SpringApplicationRunListeners listeners,
      ApplicationArguments applicationArguments) {
   // Create and configure the environment
   ConfigurableEnvironment environment = getOrCreateEnvironment();
   configureEnvironment(environment, applicationArguments.getSourceArgs());
   ConfigurationPropertySources.attach(environment);
   listeners.environmentPrepared(environment);
   bindToSpringApplication(environment);
   if (!this.isCustomEnvironment) {
      environment = new EnvironmentConverter(getClassLoader()).convertEnvironmentIfNecessary(environment,
            deduceEnvironmentClass());
   }
   ConfigurationPropertySources.attach(environment);
   return environment;
}
```

```java
private void prepareContext(ConfigurableApplicationContext context, ConfigurableEnvironment environment,
      SpringApplicationRunListeners listeners, ApplicationArguments applicationArguments, Banner printedBanner) {
   context.setEnvironment(environment);
   postProcessApplicationContext(context);
   // 执行initializers
   applyInitializers(context);
   listeners.contextPrepared(context);
   if (this.logStartupInfo) {
      logStartupInfo(context.getParent() == null);
      logStartupProfileInfo(context);
   }
   // Add boot specific singleton beans
   ConfigurableListableBeanFactory beanFactory = context.getBeanFactory();
   beanFactory.registerSingleton("springApplicationArguments", applicationArguments);
   if (printedBanner != null) {
      beanFactory.registerSingleton("springBootBanner", printedBanner);
   }
   if (beanFactory instanceof DefaultListableBeanFactory) {
      ((DefaultListableBeanFactory) beanFactory)
            .setAllowBeanDefinitionOverriding(this.allowBeanDefinitionOverriding);
   }
   if (this.lazyInitialization) {
      context.addBeanFactoryPostProcessor(new LazyInitializationBeanFactoryPostProcessor());
   }
   // Load the sources
   Set<Object> sources = getAllSources();
   Assert.notEmpty(sources, "Sources must not be empty");
   load(context, sources.toArray(new Object[0]));
   listeners.contextLoaded(context);
}
```

创建spring容器，默认org.springframework.boot.web.servlet.context.AnnotationConfigServletWebServerApplicationContext

![image-20191225093322418](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191225093322418.png)

```java
protected ConfigurableApplicationContext createApplicationContext() {
   Class<?> contextClass = this.applicationContextClass;
   if (contextClass == null) {
      try {
         switch (this.webApplicationType) {
         case SERVLET:
            contextClass = Class.forName(DEFAULT_WEB_CONTEXT_CLASS);
            break;
         case REACTIVE:
            contextClass = Class.forName(DEFAULT_REACTIVE_WEB_CONTEXT_CLASS);
            break;
         default:
            contextClass = Class.forName(DEFAULT_CONTEXT_CLASS);
         }
      }
      catch (ClassNotFoundException ex) {
         throw new IllegalStateException(
               "Unable create a default ApplicationContext, "
                     + "please specify an ApplicationContextClass",
               ex);
      }
   }
   return (ConfigurableApplicationContext) BeanUtils.instantiateClass(contextClass);
}
```

```java
private void prepareContext(ConfigurableApplicationContext context,
      ConfigurableEnvironment environment, SpringApplicationRunListeners listeners,
      ApplicationArguments applicationArguments, Banner printedBanner) {
   context.setEnvironment(environment);
   postProcessApplicationContext(context);
   // 执行Initializers
   applyInitializers(context);
   // 执行listeners
   listeners.contextPrepared(context);
   if (this.logStartupInfo) {
      logStartupInfo(context.getParent() == null);
      logStartupProfileInfo(context);
   }

   // Add boot specific singleton beans
   context.getBeanFactory().registerSingleton("springApplicationArguments",
         applicationArguments);
   if (printedBanner != null) {
      context.getBeanFactory().registerSingleton("springBootBanner", printedBanner);
   }

   // Load the sources
   Set<Object> sources = getAllSources();
   Assert.notEmpty(sources, "Sources must not be empty");
   load(context, sources.toArray(new Object[0]));
   listeners.contextLoaded(context);
}
```

org.springframework.boot.web.servlet.context.ServletWebServerApplicationContext#onRefresh

```java
protected void onRefresh() {
   super.onRefresh();
   try {
      // 实例化并启动tomcat服务器
      createWebServer();
   }
   catch (Throwable ex) {
      throw new ApplicationContextException("Unable to start web server", ex);
   }
}
```

```java
private void createWebServer() {
   WebServer webServer = this.webServer;
   ServletContext servletContext = getServletContext();
   if (webServer == null && servletContext == null) {
      // 创建webServer工厂tomcatServletWebServerFactory
      ServletWebServerFactory factory = getWebServerFactory();
     	// 创建webServer
      this.webServer = factory.getWebServer(getSelfInitializer());
   }
   else if (servletContext != null) {
      try {
         getSelfInitializer().onStartup(servletContext);
      }
      catch (ServletException ex) {
         throw new ApplicationContextException("Cannot initialize servlet context",
               ex);
      }
   }
   initPropertySources();
}
```

ServletWebServerFactoryAutoConfiguration

```java
@Configuration
@AutoConfigureOrder(Ordered.HIGHEST_PRECEDENCE)
@ConditionalOnClass(ServletRequest.class)
@ConditionalOnWebApplication(type = Type.SERVLET)
@EnableConfigurationProperties(ServerProperties.class)
// 按顺序加载，所以tomcat优先级最高
@Import({ ServletWebServerFactoryAutoConfiguration.BeanPostProcessorsRegistrar.class,
      ServletWebServerFactoryConfiguration.EmbeddedTomcat.class,
      ServletWebServerFactoryConfiguration.EmbeddedJetty.class,
      ServletWebServerFactoryConfiguration.EmbeddedUndertow.class })
public class ServletWebServerFactoryAutoConfiguration {
}



class ServletWebServerFactoryConfiguration {

	@Configuration
	@ConditionalOnClass({ Servlet.class, Tomcat.class, UpgradeProtocol.class })
	@ConditionalOnMissingBean(value = ServletWebServerFactory.class, search = SearchStrategy.CURRENT)
	public static class EmbeddedTomcat {

		@Bean
		public TomcatServletWebServerFactory tomcatServletWebServerFactory() {
      // tomcat工厂类
			return new TomcatServletWebServerFactory();
		}

	}
}
```



```java
protected ServletWebServerFactory getWebServerFactory() {
   // Use bean names so that we don't consider the hierarchy
   // 查找tomcatServletWebServerFactory的bean
   String[] beanNames = getBeanFactory()
         .getBeanNamesForType(ServletWebServerFactory.class);
   if (beanNames.length == 0) {
      throw new ApplicationContextException(
            "Unable to start ServletWebServerApplicationContext due to missing "
                  + "ServletWebServerFactory bean.");
   }
   if (beanNames.length > 1) {
      throw new ApplicationContextException(
            "Unable to start ServletWebServerApplicationContext due to multiple "
                  + "ServletWebServerFactory beans : "
                  + StringUtils.arrayToCommaDelimitedString(beanNames));
   }
   return getBeanFactory().getBean(beanNames[0], ServletWebServerFactory.class);
}
```

```java
@FunctionalInterface
public interface ServletContextInitializer {

	/**
	 * Configure the given {@link ServletContext} with any servlets, filters, listeners
	 * context-params and attributes necessary for initialization.
	 * @param servletContext the {@code ServletContext} to initialize
	 * @throws ServletException if any call against the given {@code ServletContext}
	 * throws a {@code ServletException}
	 */
	void onStartup(ServletContext servletContext) throws ServletException;

}

private org.springframework.boot.web.servlet.ServletContextInitializer getSelfInitializer() {
   // 函数接口，调用onStarup的时候调用的是selfInitialize
   return this::selfInitialize;
}

private void selfInitialize(ServletContext servletContext) throws ServletException {
   prepareWebApplicationContext(servletContext);
   ConfigurableListableBeanFactory beanFactory = getBeanFactory();
   ExistingWebApplicationScopes existingScopes = new ExistingWebApplicationScopes(
         beanFactory);
   WebApplicationContextUtils.registerWebApplicationScopes(beanFactory,
         getServletContext());
   existingScopes.restore();
   WebApplicationContextUtils.registerEnvironmentBeans(beanFactory,
         getServletContext());
   // 从spring容器里获取ServletContextInitializer bean
   for (ServletContextInitializer beans : getServletContextInitializerBeans()) {
      // 将tomcat和spring容器关联
      beans.onStartup(servletContext);
   }
}
```

```java
protected Collection<ServletContextInitializer> getServletContextInitializerBeans() {
   return new ServletContextInitializerBeans(getBeanFactory());
}

	public ServletContextInitializerBeans(ListableBeanFactory beanFactory) {
		this.initializers = new LinkedMultiValueMap<>();
    // 将ServletContextInitializerBean放入initializers
		addServletContextInitializerBeans(beanFactory);
		addAdaptableBeans(beanFactory);
		List<ServletContextInitializer> sortedInitializers = this.initializers.values()
				.stream()
				.flatMap((value) -> value.stream()
						.sorted(AnnotationAwareOrderComparator.INSTANCE))
				.collect(Collectors.toList());
		this.sortedList = Collections.unmodifiableList(sortedInitializers);
	}
```



**实例化并启动tomcat服务器**

org.springframework.boot.web.embedded.tomcat.TomcatServletWebServerFactory#getWebServer

```java
public WebServer getWebServer(ServletContextInitializer... initializers) {
   Tomcat tomcat = new Tomcat();
   File baseDir = (this.baseDirectory != null) ? this.baseDirectory
         : createTempDir("tomcat");
   tomcat.setBaseDir(baseDir.getAbsolutePath());
   Connector connector = new Connector(this.protocol);
   tomcat.getService().addConnector(connector);
   customizeConnector(connector);
   tomcat.setConnector(connector);
   tomcat.getHost().setAutoDeploy(false);
   configureEngine(tomcat.getEngine());
   for (Connector additionalConnector : this.additionalTomcatConnectors) {
      tomcat.getService().addConnector(additionalConnector);
   }
   prepareContext(tomcat.getHost(), initializers);
   // TomcatWebServer包装原生tomcat
   return getTomcatWebServer(tomcat);
}
```

org.springframework.boot.web.embedded.tomcat.TomcatWebServer#initialize

```java
private void initialize() throws WebServerException {
   TomcatWebServer.logger
         .info("Tomcat initialized with port(s): " + getPortsDescription(false));
   synchronized (this.monitor) {
      try {
         addInstanceIdToEngineName();

         Context context = findContext();
         context.addLifecycleListener((event) -> {
            if (context.equals(event.getSource())
                  && Lifecycle.START_EVENT.equals(event.getType())) {
               // Remove service connectors so that protocol binding doesn't
               // happen when the service is started.
               removeServiceConnectors();
            }
         });

         // Start the server to trigger initialization listeners
         this.tomcat.start();

         // We can re-throw failure exception directly in the main thread
         rethrowDeferredStartupExceptions();

         try {
            ContextBindings.bindClassLoader(context, context.getNamingToken(),
                  getClass().getClassLoader());
         }
         catch (NamingException ex) {
            // Naming is not enabled. Continue
         }

         // Unlike Jetty, all Tomcat threads are daemon threads. We create a
         // blocking non-daemon to stop immediate shutdown
         startDaemonAwaitThread();
      }
      catch (Exception ex) {
         stopSilently();
         throw new WebServerException("Unable to start embedded Tomcat", ex);
      }
   }
}
```

```java
protected void prepareContext(Host host, ServletContextInitializer[] initializers) {
   File documentRoot = getValidDocumentRoot();
   TomcatEmbeddedContext context = new TomcatEmbeddedContext();
   if (documentRoot != null) {
      context.setResources(new LoaderHidingResourceRoot(context));
   }
   context.setName(getContextPath());
   context.setDisplayName(getDisplayName());
   context.setPath(getContextPath());
   File docBase = (documentRoot != null) ? documentRoot
         : createTempDir("tomcat-docbase");
   context.setDocBase(docBase.getAbsolutePath());
   context.addLifecycleListener(new FixContextListener());
   context.setParentClassLoader(
         (this.resourceLoader != null) ? this.resourceLoader.getClassLoader()
               : ClassUtils.getDefaultClassLoader());
   resetDefaultLocaleMapping(context);
   addLocaleMappings(context);
   context.setUseRelativeRedirects(false);
   configureTldSkipPatterns(context);
   WebappLoader loader = new WebappLoader(context.getParentClassLoader());
   loader.setLoaderClass(TomcatEmbeddedWebappClassLoader.class.getName());
   loader.setDelegate(true);
   context.setLoader(loader);
   if (isRegisterDefaultServlet()) {
      addDefaultServlet(context);
   }
   if (shouldRegisterJspServlet()) {
      addJspServlet(context);
      addJasperInitializer(context);
   }
   context.addLifecycleListener(new StaticResourceConfigurer(context));
   ServletContextInitializer[] initializersToUse = mergeInitializers(initializers);
   host.addChild(context);
   // 实例化TomcatStarter，org.springframework.boot.web.embedded.tomcat.TomcatStarter#TomcatStarter，并发initilizer放到tomcatStarter
   configureContext(context, initializersToUse);
   postProcessContext(context);
}
```

tomcat启动的时候，org.apache.catalina.core.StandardContext#startInternal->org.springframework.boot.web.embedded.tomcat.TomcatStarter#onStartup，servlet初始化

```java
public void onStartup(Set<Class<?>> classes, ServletContext servletContext)
      throws ServletException {
   try {
      for (ServletContextInitializer initializer : this.initializers) {
         initializer.onStartup(servletContext);
      }
   }
   catch (Exception ex) {
      this.startUpException = ex;
      // Prevent Tomcat from logging and re-throwing when we know we can
      // deal with it in the main thread, but log for information here.
      if (logger.isErrorEnabled()) {
         logger.error("Error starting Tomcat context. Exception: "
               + ex.getClass().getName() + ". Message: " + ex.getMessage());
      }
   }
}
```

## 扫描路径

![image-20210105121139767](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210105121139767.png)

## 自动配置

根据import注解，导入第三方组件到spring容器，第三方组件要有自动配置类

例如mybatis

```java
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
org.mybatis.spring.boot.autoconfigure.MybatisAutoConfiguration
```

```java
@Configuration
@ConditionalOnClass({ SqlSessionFactory.class, SqlSessionFactoryBean.class })
@ConditionalOnBean(DataSource.class)
@EnableConfigurationProperties(MybatisProperties.class)
@AutoConfigureAfter(DataSourceAutoConfiguration.class)
public class MybatisAutoConfiguration {

  private static final Logger logger = LoggerFactory.getLogger(MybatisAutoConfiguration.class);

  private final MybatisProperties properties;

  private final Interceptor[] interceptors;

  private final ResourceLoader resourceLoader;

  private final DatabaseIdProvider databaseIdProvider;
  ...
}
```

### @SpringBoosApplication注解

根据import注解，解析META-INF/spring.factories文件，导入第三方组件的启动类xxxx（**org.springframework.boot.autoconfigure.EnableAutoConfiguration**=xxxx）

@SpringBootApplication->@EnableAutoConfiguration->**@Import(AutoConfigurationImportSelector.class**)



org.springframework.boot.autoconfigure.AutoConfigurationImportSelector#selectImports

```java
// 返回包里所有的org.springframework.boot.autoconfigure.EnableAutoConfiguration实现类的类名，由spring生成bd和bean	
public String[] selectImports(AnnotationMetadata annotationMetadata) {
		if (!isEnabled(annotationMetadata)) {
			return NO_IMPORTS;
		}
		AutoConfigurationMetadata autoConfigurationMetadata = AutoConfigurationMetadataLoader
				.loadMetadata(this.beanClassLoader);
		AnnotationAttributes attributes = getAttributes(annotationMetadata);
    // 解析META-INF/spring.factories文件，找到候选的配置类，key为org.springframework.boot.autoconfigure.EnableAutoConfiguration
		List<String> configurations = getCandidateConfigurations(annotationMetadata,
				attributes);
    // 去重
		configurations = removeDuplicates(configurations);
		Set<String> exclusions = getExclusions(annotationMetadata, attributes);
		checkExcludedClasses(configurations, exclusions);
    // 剔除不需要的类
		configurations.removeAll(exclusions);
    // 过滤类
		configurations = filter(configurations, autoConfigurationMetadata);
    // 先从spring.factories文件中找到监听器org.springframework.boot.autoconfigure.AutoConfigurationImportListener，然后触发该事件
		fireAutoConfigurationImportEvents(configurations, exclusions);
		return StringUtils.toStringArray(configurations);
	}
```

```java
protected List<String> getCandidateConfigurations(AnnotationMetadata metadata,
      AnnotationAttributes attributes) {
   List<String> configurations = SpringFactoriesLoader.loadFactoryNames(
         getSpringFactoriesLoaderFactoryClass(), getBeanClassLoader());
   Assert.notEmpty(configurations,
         "No auto configuration classes found in META-INF/spring.factories. If you "
               + "are using a custom packaging, make sure that file is correct.");
   return configurations;
}
```

```java
public static List<String> loadFactoryNames(Class<?> factoryClass, @Nullable ClassLoader classLoader) {
   String factoryClassName = factoryClass.getName();
   return loadSpringFactories(classLoader).getOrDefault(factoryClassName, Collections.emptyList());
}

private static Map<String, List<String>> loadSpringFactories(@Nullable ClassLoader classLoader) {
   MultiValueMap<String, String> result = cache.get(classLoader);
   if (result != null) {
      return result;
   }

   try {
     // FACTORIES_RESOURCE_LOCATION=META-INF/spring.factories
      Enumeration<URL> urls = (classLoader != null ?
            classLoader.getResources(FACTORIES_RESOURCE_LOCATION) :
            ClassLoader.getSystemResources(FACTORIES_RESOURCE_LOCATION));
      result = new LinkedMultiValueMap<>();
      // 扫描所有spring.factories文件，将文件内容放入LinkedMultiValueMap中
      while (urls.hasMoreElements()) {
         URL url = urls.nextElement();
         UrlResource resource = new UrlResource(url);
         Properties properties = PropertiesLoaderUtils.loadProperties(resource);
         for (Map.Entry<?, ?> entry : properties.entrySet()) {
            List<String> factoryClassNames = Arrays.asList(
                  StringUtils.commaDelimitedListToStringArray((String) entry.getValue()));
            result.addAll((String) entry.getKey(), factoryClassNames);
         }
      }
      cache.put(classLoader, result);
      return result;
   }
   catch (IOException ex) {
      throw new IllegalArgumentException("Unable to load factories from location [" +
            FACTORIES_RESOURCE_LOCATION + "]", ex);
   }
}
```

```java
private void fireAutoConfigurationImportEvents(List<String> configurations,
      Set<String> exclusions) {
   List<AutoConfigurationImportListener> listeners = getAutoConfigurationImportListeners();
   if (!listeners.isEmpty()) {
      AutoConfigurationImportEvent event = new AutoConfigurationImportEvent(this,
            configurations, exclusions);
      for (AutoConfigurationImportListener listener : listeners) {
         invokeAwareMethods(listener);
         listener.onAutoConfigurationImportEvent(event);
      }
   }
```



～/.m2/repository/org/springframework/boot/spring-boot-autoconfigure/2.2.6.RELEASE/spring-boot-autoconfigure-2.2.6.RELEASE.jar!/META-INF/spring.factories

```java
# Auto Configure
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
org.springframework.boot.autoconfigure.admin.SpringApplicationAdminJmxAutoConfiguration,\
org.springframework.boot.autoconfigure.aop.AopAutoConfiguration,\
org.springframework.boot.autoconfigure.amqp.RabbitAutoConfiguration,\
org.springframework.boot.autoconfigure.batch.BatchAutoConfiguration,\
org.springframework.boot.autoconfigure.cache.CacheAutoConfiguration,\
org.springframework.boot.autoconfigure.cassandra.CassandraAutoConfiguration,\
org.springframework.boot.autoconfigure.cloud.CloudServiceConnectorsAutoConfiguration,\
org.springframework.boot.autoconfigure.context.ConfigurationPropertiesAutoConfiguration,\
org.springframework.boot.autoconfigure.context.MessageSourceAutoConfiguration,\
org.springframework.boot.autoconfigure.context.PropertyPlaceholderAutoConfiguration,\
org.springframework.boot.autoconfigure.couchbase.CouchbaseAutoConfiguration,\
org.springframework.boot.autoconfigure.dao.PersistenceExceptionTranslationAutoConfiguration,\
org.springframework.boot.autoconfigure.data.cassandra.CassandraDataAutoConfiguration,\
org.springframework.boot.autoconfigure.data.cassandra.CassandraReactiveDataAutoConfiguration,\
org.springframework.boot.autoconfigure.data.cassandra.CassandraReactiveRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.cassandra.CassandraRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.couchbase.CouchbaseDataAutoConfiguration,\
org.springframework.boot.autoconfigure.data.couchbase.CouchbaseReactiveDataAutoConfiguration,\
org.springframework.boot.autoconfigure.data.couchbase.CouchbaseReactiveRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.couchbase.CouchbaseRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.elasticsearch.ElasticsearchAutoConfiguration,\
org.springframework.boot.autoconfigure.data.elasticsearch.ElasticsearchDataAutoConfiguration,\
org.springframework.boot.autoconfigure.data.elasticsearch.ElasticsearchRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.elasticsearch.ReactiveElasticsearchRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.elasticsearch.ReactiveRestClientAutoConfiguration,\
org.springframework.boot.autoconfigure.data.jdbc.JdbcRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.jpa.JpaRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.ldap.LdapRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.mongo.MongoDataAutoConfiguration,\
org.springframework.boot.autoconfigure.data.mongo.MongoReactiveDataAutoConfiguration,\
org.springframework.boot.autoconfigure.data.mongo.MongoReactiveRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.mongo.MongoRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.neo4j.Neo4jDataAutoConfiguration,\
org.springframework.boot.autoconfigure.data.neo4j.Neo4jRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.solr.SolrRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration,\
org.springframework.boot.autoconfigure.data.redis.RedisReactiveAutoConfiguration,\
org.springframework.boot.autoconfigure.data.redis.RedisRepositoriesAutoConfiguration,\
org.springframework.boot.autoconfigure.data.rest.RepositoryRestMvcAutoConfiguration,\
org.springframework.boot.autoconfigure.data.web.SpringDataWebAutoConfiguration,\
org.springframework.boot.autoconfigure.elasticsearch.jest.JestAutoConfiguration,\
org.springframework.boot.autoconfigure.elasticsearch.rest.RestClientAutoConfiguration,\
org.springframework.boot.autoconfigure.flyway.FlywayAutoConfiguration,\
org.springframework.boot.autoconfigure.freemarker.FreeMarkerAutoConfiguration,\
org.springframework.boot.autoconfigure.gson.GsonAutoConfiguration,\
org.springframework.boot.autoconfigure.h2.H2ConsoleAutoConfiguration,\
org.springframework.boot.autoconfigure.hateoas.HypermediaAutoConfiguration,\
org.springframework.boot.autoconfigure.hazelcast.HazelcastAutoConfiguration,\
org.springframework.boot.autoconfigure.hazelcast.HazelcastJpaDependencyAutoConfiguration,\
org.springframework.boot.autoconfigure.http.HttpMessageConvertersAutoConfiguration,\
org.springframework.boot.autoconfigure.http.codec.CodecsAutoConfiguration,\
org.springframework.boot.autoconfigure.influx.InfluxDbAutoConfiguration,\
org.springframework.boot.autoconfigure.info.ProjectInfoAutoConfiguration,\
org.springframework.boot.autoconfigure.integration.IntegrationAutoConfiguration,\
org.springframework.boot.autoconfigure.jackson.JacksonAutoConfiguration,\
org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration,\
org.springframework.boot.autoconfigure.jdbc.JdbcTemplateAutoConfiguration,\
org.springframework.boot.autoconfigure.jdbc.JndiDataSourceAutoConfiguration,\
org.springframework.boot.autoconfigure.jdbc.XADataSourceAutoConfiguration,\
org.springframework.boot.autoconfigure.jdbc.DataSourceTransactionManagerAutoConfiguration,\
org.springframework.boot.autoconfigure.jms.JmsAutoConfiguration,\
org.springframework.boot.autoconfigure.jmx.JmxAutoConfiguration,\
org.springframework.boot.autoconfigure.jms.JndiConnectionFactoryAutoConfiguration,\
org.springframework.boot.autoconfigure.jms.activemq.ActiveMQAutoConfiguration,\
org.springframework.boot.autoconfigure.jms.artemis.ArtemisAutoConfiguration,\
org.springframework.boot.autoconfigure.groovy.template.GroovyTemplateAutoConfiguration,\
org.springframework.boot.autoconfigure.jersey.JerseyAutoConfiguration,\
org.springframework.boot.autoconfigure.jooq.JooqAutoConfiguration,\
org.springframework.boot.autoconfigure.jsonb.JsonbAutoConfiguration,\
org.springframework.boot.autoconfigure.kafka.KafkaAutoConfiguration,\
org.springframework.boot.autoconfigure.ldap.embedded.EmbeddedLdapAutoConfiguration,\
org.springframework.boot.autoconfigure.ldap.LdapAutoConfiguration,\
org.springframework.boot.autoconfigure.liquibase.LiquibaseAutoConfiguration,\
org.springframework.boot.autoconfigure.mail.MailSenderAutoConfiguration,\
org.springframework.boot.autoconfigure.mail.MailSenderValidatorAutoConfiguration,\
org.springframework.boot.autoconfigure.mongo.embedded.EmbeddedMongoAutoConfiguration,\
org.springframework.boot.autoconfigure.mongo.MongoAutoConfiguration,\
org.springframework.boot.autoconfigure.mongo.MongoReactiveAutoConfiguration,\
org.springframework.boot.autoconfigure.mustache.MustacheAutoConfiguration,\
org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration,\
org.springframework.boot.autoconfigure.quartz.QuartzAutoConfiguration,\
org.springframework.boot.autoconfigure.rsocket.RSocketMessagingAutoConfiguration,\
org.springframework.boot.autoconfigure.rsocket.RSocketRequesterAutoConfiguration,\
org.springframework.boot.autoconfigure.rsocket.RSocketServerAutoConfiguration,\
org.springframework.boot.autoconfigure.rsocket.RSocketStrategiesAutoConfiguration,\
org.springframework.boot.autoconfigure.security.servlet.SecurityAutoConfiguration,\
org.springframework.boot.autoconfigure.security.servlet.UserDetailsServiceAutoConfiguration,\
org.springframework.boot.autoconfigure.security.servlet.SecurityFilterAutoConfiguration,\
org.springframework.boot.autoconfigure.security.reactive.ReactiveSecurityAutoConfiguration,\
org.springframework.boot.autoconfigure.security.reactive.ReactiveUserDetailsServiceAutoConfiguration,\
org.springframework.boot.autoconfigure.security.rsocket.RSocketSecurityAutoConfiguration,\
org.springframework.boot.autoconfigure.security.saml2.Saml2RelyingPartyAutoConfiguration,\
org.springframework.boot.autoconfigure.sendgrid.SendGridAutoConfiguration,\
org.springframework.boot.autoconfigure.session.SessionAutoConfiguration,\
org.springframework.boot.autoconfigure.security.oauth2.client.servlet.OAuth2ClientAutoConfiguration,\
org.springframework.boot.autoconfigure.security.oauth2.client.reactive.ReactiveOAuth2ClientAutoConfiguration,\
org.springframework.boot.autoconfigure.security.oauth2.resource.servlet.OAuth2ResourceServerAutoConfiguration,\
org.springframework.boot.autoconfigure.security.oauth2.resource.reactive.ReactiveOAuth2ResourceServerAutoConfiguration,\
org.springframework.boot.autoconfigure.solr.SolrAutoConfiguration,\
org.springframework.boot.autoconfigure.task.TaskExecutionAutoConfiguration,\
org.springframework.boot.autoconfigure.task.TaskSchedulingAutoConfiguration,\
org.springframework.boot.autoconfigure.thymeleaf.ThymeleafAutoConfiguration,\
org.springframework.boot.autoconfigure.transaction.TransactionAutoConfiguration,\
org.springframework.boot.autoconfigure.transaction.jta.JtaAutoConfiguration,\
org.springframework.boot.autoconfigure.validation.ValidationAutoConfiguration,\
org.springframework.boot.autoconfigure.web.client.RestTemplateAutoConfiguration,\
org.springframework.boot.autoconfigure.web.embedded.EmbeddedWebServerFactoryCustomizerAutoConfiguration,\
org.springframework.boot.autoconfigure.web.reactive.HttpHandlerAutoConfiguration,\
org.springframework.boot.autoconfigure.web.reactive.ReactiveWebServerFactoryAutoConfiguration,\
org.springframework.boot.autoconfigure.web.reactive.WebFluxAutoConfiguration,\
org.springframework.boot.autoconfigure.web.reactive.error.ErrorWebFluxAutoConfiguration,\
org.springframework.boot.autoconfigure.web.reactive.function.client.ClientHttpConnectorAutoConfiguration,\
org.springframework.boot.autoconfigure.web.reactive.function.client.WebClientAutoConfiguration,\
org.springframework.boot.autoconfigure.web.servlet.DispatcherServletAutoConfiguration,\
org.springframework.boot.autoconfigure.web.servlet.ServletWebServerFactoryAutoConfiguration,\
org.springframework.boot.autoconfigure.web.servlet.error.ErrorMvcAutoConfiguration,\
org.springframework.boot.autoconfigure.web.servlet.HttpEncodingAutoConfiguration,\
org.springframework.boot.autoconfigure.web.servlet.MultipartAutoConfiguration,\
org.springframework.boot.autoconfigure.web.servlet.WebMvcAutoConfiguration,\
org.springframework.boot.autoconfigure.websocket.reactive.WebSocketReactiveAutoConfiguration,\
org.springframework.boot.autoconfigure.websocket.servlet.WebSocketServletAutoConfiguration,\
org.springframework.boot.autoconfigure.websocket.servlet.WebSocketMessagingAutoConfiguration,\
org.springframework.boot.autoconfigure.webservices.WebServicesAutoConfiguration,\
org.springframework.boot.autoconfigure.webservices.client.WebServiceTemplateAutoConfiguration
```



## 自动配置注入dispatcherServlet

**springboot是先把dispatcherServlet bean注入到spring容器，而springmvc不需要**

注入的DispatcherServletRegistrationBean，继承了ServletContextInitializer，能被启动服务器流程调用

spring.factories

```java
org.springframework.boot.autoconfigure.EnableAutoConfiguration=org.springframework.boot.autoconfigure.web.servlet.DispatcherServletAutoConfiguration
```

```java
@AutoConfigureOrder(Ordered.HIGHEST_PRECEDENCE)
@Configuration
@ConditionalOnWebApplication(type = Type.SERVLET)
@ConditionalOnClass(DispatcherServlet.class)
@AutoConfigureAfter(ServletWebServerFactoryAutoConfiguration.class)
@EnableConfigurationProperties(ServerProperties.class)
public class DispatcherServletAutoConfiguration {
  
  
  @Configuration
	@Conditional(DispatcherServletRegistrationCondition.class)
	@ConditionalOnClass(ServletRegistration.class)
	@EnableConfigurationProperties(WebMvcProperties.class)
	@Import(DispatcherServletConfiguration.class)
	protected static class DispatcherServletRegistrationConfiguration {
    
      // 注入DispatcherServletRegistrationBean，这个bean继承了
      @Bean(name = DEFAULT_DISPATCHER_SERVLET_REGISTRATION_BEAN_NAME)
      @ConditionalOnBean(value = DispatcherServlet.class, name = DEFAULT_DISPATCHER_SERVLET_BEAN_NAME)
      public DispatcherServletRegistrationBean dispatcherServletRegistration(
          DispatcherServlet dispatcherServlet) {
        DispatcherServletRegistrationBean registration = new DispatcherServletRegistrationBean(
            dispatcherServlet, this.serverProperties.getServlet().getPath());
        registration.setName(DEFAULT_DISPATCHER_SERVLET_BEAN_NAME);
        registration.setLoadOnStartup(
            this.webMvcProperties.getServlet().getLoadOnStartup());
        if (this.multipartConfig != null) {
          registration.setMultipartConfig(this.multipartConfig);
        }
        return registration;
      }
  }
  
  
  @Configuration
	@Conditional(DefaultDispatcherServletCondition.class)
	@ConditionalOnClass(ServletRegistration.class)
	@EnableConfigurationProperties(WebMvcProperties.class)
	protected static class DispatcherServletConfiguration {

		private final WebMvcProperties webMvcProperties;

		public DispatcherServletConfiguration(WebMvcProperties webMvcProperties) {
			this.webMvcProperties = webMvcProperties;
		}

    // 注入dispatcherServlet bean
		@Bean(name = DEFAULT_DISPATCHER_SERVLET_BEAN_NAME)
		public DispatcherServlet dispatcherServlet() {
			DispatcherServlet dispatcherServlet = new DispatcherServlet();
			dispatcherServlet.setDispatchOptionsRequest(
					this.webMvcProperties.isDispatchOptionsRequest());
			dispatcherServlet.setDispatchTraceRequest(
					this.webMvcProperties.isDispatchTraceRequest());
			dispatcherServlet.setThrowExceptionIfNoHandlerFound(
					this.webMvcProperties.isThrowExceptionIfNoHandlerFound());
			return dispatcherServlet;
		}
  }
  
  
}
```

![image-20191225162114063](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191225162114063.png)

```java
public final void onStartup(ServletContext servletContext) throws ServletException {
   String description = getDescription();
   if (!isEnabled()) {
      logger.info(StringUtils.capitalize(description)
            + " was not registered (disabled)");
      return;
   }
   register(description, servletContext);
}

protected final void register(String description, ServletContext servletContext) {
   D registration = addRegistration(description, servletContext);
   if (registration == null) {
      logger.info(StringUtils.capitalize(description) + " was not registered "
            + "(possibly already registered?)");
      return;
   }
   configure(registration);
}

// 将dispatcherServlet设置到tomcat的context里，作为一个分发请求的servlet
protected ServletRegistration.Dynamic addRegistration(String description,
                                                      ServletContext servletContext) {
  String name = getServletName();
  logger.info("Servlet " + name + " mapped to " + this.urlMappings);
  return servletContext.addServlet(name, this.servlet);
}

protected void configure(ServletRegistration.Dynamic registration) {
		super.configure(registration);
		String[] urlMapping = StringUtils.toStringArray(this.urlMappings);
		if (urlMapping.length == 0 && this.alwaysMapUrl) {
			urlMapping = DEFAULT_MAPPINGS;
		}
		if (!ObjectUtils.isEmpty(urlMapping)) {
			registration.addMapping(urlMapping);
		}
		registration.setLoadOnStartup(this.loadOnStartup);
		if (this.multipartConfig != null) {
			registration.setMultipartConfig(this.multipartConfig);
		}
	}
```

dispatcherServlet 实现了ApplicationContextAware接口，在org.springframework.web.servlet.FrameworkServlet#setApplicationContext中设置了spring上下文

```java
public void setApplicationContext(ApplicationContext applicationContext) {
   if (this.webApplicationContext == null && applicationContext instanceof WebApplicationContext) {
      this.webApplicationContext = (WebApplicationContext) applicationContext;
      this.webApplicationContextInjected = true;
   }
}
```

所以说dispatcherServlet bean要先在spring容器里面，再利用后置处理器设置上下文，而springmvc的dispatcherServlet则不需要再spring容器

## 自动配置WebMvcAutoConfiguration

```java
// 搜集messageConvertersProvider消息转换器等bean
public WebMvcAutoConfigurationAdapter(ResourceProperties resourceProperties,
      WebMvcProperties mvcProperties, ListableBeanFactory beanFactory,
      ObjectProvider<HttpMessageConverters> messageConvertersProvider,
      ObjectProvider<ResourceHandlerRegistrationCustomizer> resourceHandlerRegistrationCustomizerProvider) {
   this.resourceProperties = resourceProperties;
   this.mvcProperties = mvcProperties;
   this.beanFactory = beanFactory;
   this.messageConvertersProvider = messageConvertersProvider;
   this.resourceHandlerRegistrationCustomizer = resourceHandlerRegistrationCustomizerProvider
         .getIfAvailable();
}
```

视图解析器

```java
@Bean
@ConditionalOnBean(ViewResolver.class)
@ConditionalOnMissingBean(name = "viewResolver", value = ContentNegotiatingViewResolver.class)
public ContentNegotiatingViewResolver viewResolver(BeanFactory beanFactory) {
   ContentNegotiatingViewResolver resolver = new ContentNegotiatingViewResolver();
   resolver.setContentNegotiationManager(
         beanFactory.getBean(ContentNegotiationManager.class));
   // ContentNegotiatingViewResolver uses all the other view resolvers to locate
   // a view so it should have a high precedence
   resolver.setOrder(Ordered.HIGHEST_PRECEDENCE);
   return resolver;
}
```

```java
protected void initServletContext(ServletContext servletContext) {
   Collection<ViewResolver> matchingBeans =
         BeanFactoryUtils.beansOfTypeIncludingAncestors(obtainApplicationContext(), ViewResolver.class).values();
   if (this.viewResolvers == null) {
      this.viewResolvers = new ArrayList<>(matchingBeans.size());
      for (ViewResolver viewResolver : matchingBeans) {
         if (this != viewResolver) {
            this.viewResolvers.add(viewResolver);
         }
      }
   }
   else {
      for (int i = 0; i < this.viewResolvers.size(); i++) {
         ViewResolver vr = this.viewResolvers.get(i);
         if (matchingBeans.contains(vr)) {
            continue;
         }
         String name = vr.getClass().getName() + i;
         obtainApplicationContext().getAutowireCapableBeanFactory().initializeBean(vr, name);
      }

   }
   if (this.viewResolvers.isEmpty()) {
      logger.warn("Did not find any ViewResolvers to delegate to; please configure them using the " +
            "'viewResolvers' property on the ContentNegotiatingViewResolver");
   }
   AnnotationAwareOrderComparator.sort(this.viewResolvers);
   this.cnmFactoryBean.setServletContext(servletContext);
}
```

## starter

## 配置文件

```java
@Configuration
public class BeanConfig {

    @Bean
    @ConfigurationProperties("person")
    public Person person(){
        return new Person();
    }

}
```

```yaml
person:
  name: test
```

@ConfigurationProperties

@ConfigurationProperties的解析就是通过一个后置处理器：**ConfigurationPropertiesBindingPostProcessor**来实现的



## springcloud

spring.factories

```java
# AutoConfiguration
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
org.springframework.cloud.autoconfigure.ConfigurationPropertiesRebinderAutoConfiguration,\
org.springframework.cloud.autoconfigure.LifecycleMvcEndpointAutoConfiguration,\
org.springframework.cloud.autoconfigure.RefreshAutoConfiguration,\
org.springframework.cloud.autoconfigure.RefreshEndpointAutoConfiguration,\
org.springframework.cloud.autoconfigure.WritableEnvironmentEndpointAutoConfiguration
# Application Listeners
org.springframework.context.ApplicationListener=\
org.springframework.cloud.bootstrap.BootstrapApplicationListener,\
org.springframework.cloud.bootstrap.LoggingSystemShutdownListener,\
org.springframework.cloud.context.restart.RestartListener
# Bootstrap components
org.springframework.cloud.bootstrap.BootstrapConfiguration=\
org.springframework.cloud.bootstrap.config.PropertySourceBootstrapConfiguration,\
org.springframework.cloud.bootstrap.encrypt.EncryptionBootstrapConfiguration,\
org.springframework.cloud.autoconfigure.ConfigurationPropertiesRebinderAutoConfiguration,\
org.springframework.boot.autoconfigure.context.PropertyPlaceholderAutoConfiguration,\
org.springframework.cloud.util.random.CachedRandomPropertySourceAutoConfiguration
```

Spring Cloud的BootstrapApplicationListener监听ApplicationEnvironmentPreparedEvent事件，在监听到事件时开启一个新的ApplicationContext容器，我们可以称这个ApplicationContext容器为Spring Cloud的Bootstrap容器。

```java
public class BootstrapApplicationListener
      implements ApplicationListener<ApplicationEnvironmentPreparedEvent>, Ordered 
```

在springboot发出ApplicationEnvironmentPreparedEvent事件的时候，spring cloud的监听器被激活

org.springframework.cloud.bootstrap.BootstrapApplicationListener#onApplicationEvent

```java
public void onApplicationEvent(ApplicationEnvironmentPreparedEvent event) {
		ConfigurableEnvironment environment = event.getEnvironment();
		if (!environment.getProperty("spring.cloud.bootstrap.enabled", Boolean.class,
				true)) {
			return;
		}
		// don't listen to events in a bootstrap context
		if (environment.getPropertySources().contains(BOOTSTRAP_PROPERTY_SOURCE_NAME)) {
			return;
		}
		ConfigurableApplicationContext context = null;
		String configName = environment
				.resolvePlaceholders("${spring.cloud.bootstrap.name:bootstrap}");
		for (ApplicationContextInitializer<?> initializer : event.getSpringApplication()
				.getInitializers()) {
      // 查找ParentContextApplicationContextInitializer初始化器
			if (initializer instanceof ParentContextApplicationContextInitializer) {
				context = findBootstrapContext(
						(ParentContextApplicationContextInitializer) initializer,
						configName);
			}
		}
		if (context == null) {
      // 创建applicationConetxt
			context = bootstrapServiceContext(environment, event.getSpringApplication(),
					configName);
			event.getSpringApplication()
					.addListeners(new CloseContextOnFailureApplicationListener(context));
		}

		apply(context, event.getSpringApplication(), environment);
	}

	private void apply(ConfigurableApplicationContext context,
			SpringApplication application, ConfigurableEnvironment environment) {
		if (application.getAllSources().contains(BootstrapMarkerConfiguration.class)) {
			return;
		}
		application.addPrimarySources(Arrays.asList(BootstrapMarkerConfiguration.class));
		@SuppressWarnings("rawtypes")
		Set target = new LinkedHashSet<>(application.getInitializers());
		target.addAll(
				getOrderedBeansOfType(context, ApplicationContextInitializer.class));
		application.setInitializers(target);
		addBootstrapDecryptInitializer(application);
	}
```





org.springframework.cloud.bootstrap.BootstrapApplicationListener#bootstrapServiceContext

```java
private ConfigurableApplicationContext bootstrapServiceContext(
      ConfigurableEnvironment environment, final SpringApplication application,
      String configName) {
   StandardEnvironment bootstrapEnvironment = new StandardEnvironment();
   MutablePropertySources bootstrapProperties = bootstrapEnvironment
         .getPropertySources();
  // 清空PropertySource
   for (PropertySource<?> source : bootstrapProperties) {
      bootstrapProperties.remove(source.getName());
   }
   String configLocation = environment
         .resolvePlaceholders("${spring.cloud.bootstrap.location:}");
   String configAdditionalLocation = environment
         .resolvePlaceholders("${spring.cloud.bootstrap.additional-location:}");
   Map<String, Object> bootstrapMap = new HashMap<>();
  // configName ${spring.cloud.bootstrap.name:bootstrap}
   bootstrapMap.put("spring.config.name", configName);
   // if an app (or test) uses spring.main.web-application-type=reactive, bootstrap
   // will fail
   // force the environment to use none, because if though it is set below in the
   // builder
   // the environment overrides it
   bootstrapMap.put("spring.main.web-application-type", "none");
   if (StringUtils.hasText(configLocation)) {
      bootstrapMap.put("spring.config.location", configLocation);
   }
   if (StringUtils.hasText(configAdditionalLocation)) {
      bootstrapMap.put("spring.config.additional-location",
            configAdditionalLocation);
   }
  	
   //bootstrapMap = {HashMap@2715}  size = 2
 	// "spring.config.name" -> "bootstrap"
  // "spring.main.web-application-type" -> "none"
   bootstrapProperties.addFirst(
         new MapPropertySource(BOOTSTRAP_PROPERTY_SOURCE_NAME, bootstrapMap));
   for (PropertySource<?> source : environment.getPropertySources()) {
      if (source instanceof StubPropertySource) {
         continue;
      }
      bootstrapProperties.addLast(source);
   }
   // TODO: is it possible or sensible to share a ResourceLoader?
   SpringApplicationBuilder builder = new SpringApplicationBuilder()
         .profiles(environment.getActiveProfiles()).bannerMode(Mode.OFF)
         .environment(bootstrapEnvironment)
         // Don't use the default properties in this builder
         .registerShutdownHook(false).logStartupInfo(false)
         .web(WebApplicationType.NONE);
   final SpringApplication builderApplication = builder.application();
   if (builderApplication.getMainApplicationClass() == null) {
      // gh_425:
      // SpringApplication cannot deduce the MainApplicationClass here
      // if it is booted from SpringBootServletInitializer due to the
      // absense of the "main" method in stackTraces.
      // But luckily this method's second parameter "application" here
      // carries the real MainApplicationClass which has been explicitly
      // set by SpringBootServletInitializer itself already.
      builder.main(application.getMainApplicationClass());
   }
   if (environment.getPropertySources().contains("refreshArgs")) {
      // If we are doing a context refresh, really we only want to refresh the
      // Environment, and there are some toxic listeners (like the
      // LoggingApplicationListener) that affect global static state, so we need a
      // way to switch those off.
      builderApplication
            .setListeners(filterListeners(builderApplication.getListeners()));
   }
   // 设置配置类
   builder.sources(BootstrapImportSelectorConfiguration.class);
   final ConfigurableApplicationContext context = builder.run();
   // gh-214 using spring.application.name=bootstrap to set the context id via
   // `ContextIdApplicationContextInitializer` prevents apps from getting the actual
   // spring.application.name
   // during the bootstrap phase.
   context.setId("bootstrap");
   // Make the bootstrap context a parent of the app context
   // 设置application的父容器是context
   addAncestorInitializer(application, context);
   // It only has properties in it now that we don't want in the parent so remove
   // it (and it will be added back later)
   bootstrapProperties.remove(BOOTSTRAP_PROPERTY_SOURCE_NAME);
   mergeDefaultProperties(environment.getPropertySources(), bootstrapProperties);
   return context;
}
```

```java
@Configuration(proxyBeanMethods = false)
@Import(BootstrapImportSelector.class)
public class BootstrapImportSelectorConfiguration {

}
```

org.springframework.cloud.bootstrap.BootstrapImportSelector#selectImports

```java
public String[] selectImports(AnnotationMetadata annotationMetadata) {
   ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
   // Use names and ensure unique to protect against duplicates
   // 注册BootstrapConfiguration.class配置类
   List<String> names = new ArrayList<>(SpringFactoriesLoader
         .loadFactoryNames(BootstrapConfiguration.class, classLoader));
   names.addAll(Arrays.asList(StringUtils.commaDelimitedListToStringArray(
         this.environment.getProperty("spring.cloud.bootstrap.sources", ""))));

   List<OrderedAnnotatedElement> elements = new ArrayList<>();
   for (String name : names) {
      try {
         elements.add(
               new OrderedAnnotatedElement(this.metadataReaderFactory, name));
      }
      catch (IOException e) {
         continue;
      }
   }
   AnnotationAwareOrderComparator.sort(elements);

   String[] classNames = elements.stream().map(e -> e.name).toArray(String[]::new);

   return classNames;
}
```



创建父容器，一开始创建的容器为子容器，通过祖先初始化器来实现

```java
private void addAncestorInitializer(SpringApplication application,
      ConfigurableApplicationContext context) {
   boolean installed = false;
   for (ApplicationContextInitializer<?> initializer : application
         .getInitializers()) {
      if (initializer instanceof AncestorInitializer) {
         installed = true;
         // New parent
         ((AncestorInitializer) initializer).setParent(context);
      }
   }
   if (!installed) {
      application.addInitializers(new AncestorInitializer(context));
   }

}
```

![image-20210806155448364](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210806155448364.png)



```java
private void load(PropertySourceLoader loader, String location, Profile profile, DocumentFilter filter,
      DocumentConsumer consumer) {
   Resource[] resources = getResources(location);
   for (Resource resource : resources) {
      try {
         if (resource == null || !resource.exists()) {
            if (this.logger.isTraceEnabled()) {
               StringBuilder description = getDescription("Skipped missing config ", location, resource,
                     profile);
               this.logger.trace(description);
            }
            continue;
         }
         if (!StringUtils.hasText(StringUtils.getFilenameExtension(resource.getFilename()))) {
            if (this.logger.isTraceEnabled()) {
               StringBuilder description = getDescription("Skipped empty config extension ", location,
                     resource, profile);
               this.logger.trace(description);
            }
            continue;
         }
         String name = "applicationConfig: [" + getLocationName(location, resource) + "]";
         // 加载application.yml配置文件
         List<Document> documents = loadDocuments(loader, name, resource);
         if (CollectionUtils.isEmpty(documents)) {
            if (this.logger.isTraceEnabled()) {
               StringBuilder description = getDescription("Skipped unloaded config ", location, resource,
                     profile);
               this.logger.trace(description);
            }
            continue;
         }
         List<Document> loaded = new ArrayList<>();
         for (Document document : documents) {
            if (filter.match(document)) {
               // 获取active profile，放入this.profiles，外围会死循环this.profiles
               addActiveProfiles(document.getActiveProfiles());
               addIncludedProfiles(document.getIncludeProfiles());
               loaded.add(document);
            }
         }
         Collections.reverse(loaded);
         if (!loaded.isEmpty()) {
            loaded.forEach((document) -> consumer.accept(profile, document));
            if (this.logger.isDebugEnabled()) {
               StringBuilder description = getDescription("Loaded config file ", location, resource,
                     profile);
               this.logger.debug(description);
            }
         }
      }
      catch (Exception ex) {
         StringBuilder description = getDescription("Failed to load property source from ", location,
               resource, profile);
         throw new IllegalStateException(description.toString(), ex);
      }
   }
}
```

![image-20210806155333014](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210806155333014.png)



![image-20210806155250556](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210806155250556.png)

BootStrap Application 容器的作用：
**提前加载SpringCloud 相关的配置类，比如BootStrap Application会提前加载配置中心相关配置类，优先加读取`bootstrap`配置文件等逻辑。**

```java
# Auto Configure
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
org.springframework.cloud.config.client.ConfigClientAutoConfiguration

# Bootstrap components
org.springframework.cloud.bootstrap.BootstrapConfiguration=\
org.springframework.cloud.config.client.ConfigServiceBootstrapConfiguration,\
org.springframework.cloud.config.client.DiscoveryClientConfigServiceBootstrapConfiguration
```

```java
@Configuration
@EnableConfigurationProperties
public class ConfigServiceBootstrapConfiguration {

	@Autowired
	private ConfigurableEnvironment environment;

	@Bean
	public ConfigClientProperties configClientProperties() {
		ConfigClientProperties client = new ConfigClientProperties(this.environment);
		return client;
	}

	@Bean
	@ConditionalOnMissingBean(ConfigServicePropertySourceLocator.class)
	@ConditionalOnProperty(value = "spring.cloud.config.enabled", matchIfMissing = true)
	public ConfigServicePropertySourceLocator configServicePropertySource(ConfigClientProperties properties) {
		ConfigServicePropertySourceLocator locator = new ConfigServicePropertySourceLocator(
				properties);
		return locator;
	}

	@ConditionalOnProperty(value = "spring.cloud.config.failFast", matchIfMissing=false)
	@ConditionalOnClass({ Retryable.class, Aspect.class, AopAutoConfiguration.class })
	@Configuration
	@EnableRetry(proxyTargetClass = true)
	@Import(AopAutoConfiguration.class)
	@EnableConfigurationProperties(RetryProperties.class)
	protected static class RetryConfiguration {

		@Bean
		@ConditionalOnMissingBean(name = "configServerRetryInterceptor")
		public RetryOperationsInterceptor configServerRetryInterceptor(
				RetryProperties properties) {
			return RetryInterceptorBuilder
					.stateless()
					.backOffOptions(properties.getInitialInterval(),
							properties.getMultiplier(), properties.getMaxInterval())
					.maxAttempts(properties.getMaxAttempts()).build();
		}
	}

}
```

org.springframework.boot.SpringApplication#prepareEnvironment

```
listeners.environmentPrepared(environment);
```

org.springframework.cloud.bootstrap.BootstrapApplicationListener#onApplicationEvent

```java
public void onApplicationEvent(ApplicationEnvironmentPreparedEvent event) {
   ConfigurableEnvironment environment = event.getEnvironment();
   if (!environment.getProperty("spring.cloud.bootstrap.enabled", Boolean.class,
         true)) {
      return;
   }
   // don't listen to events in a bootstrap context
   if (environment.getPropertySources().contains(BOOTSTRAP_PROPERTY_SOURCE_NAME)) {
      return;
   }
   ConfigurableApplicationContext context = null;
   String configName = environment
         .resolvePlaceholders("${spring.cloud.bootstrap.name:bootstrap}");
   for (ApplicationContextInitializer<?> initializer : event.getSpringApplication()
         .getInitializers()) {
      if (initializer instanceof ParentContextApplicationContextInitializer) {
         context = findBootstrapContext(
               (ParentContextApplicationContextInitializer) initializer,
               configName);
      }
   }
   if (context == null) {
      // 创建一个新的Spring容器
      context = bootstrapServiceContext(environment, event.getSpringApplication(),
            configName);
      event.getSpringApplication()
            .addListeners(new CloseContextOnFailureApplicationListener(context));
   }

   apply(context, event.getSpringApplication(), environment);
}
```

```java
private ConfigurableApplicationContext bootstrapServiceContext(
      ConfigurableEnvironment environment, final SpringApplication application,
      String configName) {
   StandardEnvironment bootstrapEnvironment = new StandardEnvironment();
   MutablePropertySources bootstrapProperties = bootstrapEnvironment
         .getPropertySources();
   for (PropertySource<?> source : bootstrapProperties) {
      bootstrapProperties.remove(source.getName());
   }
   String configLocation = environment
         .resolvePlaceholders("${spring.cloud.bootstrap.location:}");
   String configAdditionalLocation = environment
         .resolvePlaceholders("${spring.cloud.bootstrap.additional-location:}");
   Map<String, Object> bootstrapMap = new HashMap<>();
   bootstrapMap.put("spring.config.name", configName);
   // if an app (or test) uses spring.main.web-application-type=reactive, bootstrap
   // will fail
   // force the environment to use none, because if though it is set below in the
   // builder
   // the environment overrides it
   bootstrapMap.put("spring.main.web-application-type", "none");
   if (StringUtils.hasText(configLocation)) {
      bootstrapMap.put("spring.config.location", configLocation);
   }
   if (StringUtils.hasText(configAdditionalLocation)) {
      bootstrapMap.put("spring.config.additional-location",
            configAdditionalLocation);
   }
   bootstrapProperties.addFirst(
         new MapPropertySource(BOOTSTRAP_PROPERTY_SOURCE_NAME, bootstrapMap));
   for (PropertySource<?> source : environment.getPropertySources()) {
      if (source instanceof StubPropertySource) {
         continue;
      }
      bootstrapProperties.addLast(source);
   }
   // TODO: is it possible or sensible to share a ResourceLoader?
   SpringApplicationBuilder builder = new SpringApplicationBuilder()
         .profiles(environment.getActiveProfiles()).bannerMode(Mode.OFF)
         .environment(bootstrapEnvironment)
         // Don't use the default properties in this builder
         .registerShutdownHook(false).logStartupInfo(false)
         .web(WebApplicationType.NONE);
   final SpringApplication builderApplication = builder.application();
   if (builderApplication.getMainApplicationClass() == null) {
      // gh_425:
      // SpringApplication cannot deduce the MainApplicationClass here
      // if it is booted from SpringBootServletInitializer due to the
      // absense of the "main" method in stackTraces.
      // But luckily this method's second parameter "application" here
      // carries the real MainApplicationClass which has been explicitly
      // set by SpringBootServletInitializer itself already.
      builder.main(application.getMainApplicationClass());
   }
   if (environment.getPropertySources().contains("refreshArgs")) {
      // If we are doing a context refresh, really we only want to refresh the
      // Environment, and there are some toxic listeners (like the
      // LoggingApplicationListener) that affect global static state, so we need a
      // way to switch those off.
      builderApplication
            .setListeners(filterListeners(builderApplication.getListeners()));
   }
  // 设置source BootstrapImportSelector
   builder.sources(BootstrapImportSelectorConfiguration.class);
  	// application.run()执行run，再次唤起所有监听器
   final ConfigurableApplicationContext context = builder.run();
   // gh-214 using spring.application.name=bootstrap to set the context id via
   // `ContextIdApplicationContextInitializer` prevents apps from getting the actual
   // spring.application.name
   // during the bootstrap phase.
   context.setId("bootstrap");
   // Make the bootstrap context a parent of the app context
   // 设置springboot应用的AncestorInitializer，后续执行初始化的时候设置父容器为springcloud应用
   addAncestorInitializer(application, context);
   // It only has properties in it now that we don't want in the parent so remove
   // it (and it will be added back later)
   bootstrapProperties.remove(BOOTSTRAP_PROPERTY_SOURCE_NAME);
   mergeDefaultProperties(environment.getPropertySources(), bootstrapProperties);
   return context;
}
```

在BootstrapApplicationListener监听器中会将BootstrapImportSelectorConfiguration配置类注入到IOC容器，配置类上有一个@Import注解将BootstrapImportSelector类注入容器并获取spring.factories配置中key为org.springframework.cloud.bootstrap.BootstrapConfiguration的配置组件

```java
@Configuration(proxyBeanMethods = false)
@Import(BootstrapImportSelector.class)
public class BootstrapImportSelectorConfiguration {

}
```

BootstrapImportSelector类是DeferredImportSelector个延迟selector，会在所有的类加载完成后加载spring.factories配置文件中的配置：

```java
public class BootstrapImportSelector implements EnvironmentAware, DeferredImportSelector {

	private Environment environment;

	private MetadataReaderFactory metadataReaderFactory = new CachingMetadataReaderFactory();

	@Override
	public void setEnvironment(Environment environment) {
		this.environment = environment;
	}

	@Override
	public String[] selectImports(AnnotationMetadata annotationMetadata) {
    //获取当前的类加载器
		ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
		// 通过SpringFactoriesLoader获取配置spring.factories中key为org.springframework.cloud.bootstrap.BootstrapConfiguration的组件
//    org.springframework.cloud.bootstrap.BootstrapConfiguration=\
//org.springframework.cloud.bootstrap.config.PropertySourceBootstrapConfiguration,\
//org.springframework.cloud.bootstrap.encrypt.EncryptionBootstrapConfiguration,\
//org.springframework.cloud.autoconfigure.ConfigurationPropertiesRebinderAutoConfiguration,\
//org.springframework.boot.autoconfigure.context.PropertyPlaceholderAutoConfiguration,\
//org.springframework.cloud.util.random.CachedRandomPropertySourceAutoConfiguration
		List<String> names = new ArrayList<>(SpringFactoriesLoader
				.loadFactoryNames(BootstrapConfiguration.class, classLoader));
    //获取属性配置文件中key为spring.cloud.bootstrap.sources的组件，并将其加入到集合
		names.addAll(Arrays.asList(StringUtils.commaDelimitedListToStringArray(
				this.environment.getProperty("spring.cloud.bootstrap.sources", ""))));

		List<OrderedAnnotatedElement> elements = new ArrayList<>();
		for (String name : names) {
			try {
        // 将组将包装成OrderedAnnotatedElement对象加入集合，包含类名、order对象、order值
				elements.add(
						new OrderedAnnotatedElement(this.metadataReaderFactory, name));
			}
			catch (IOException e) {
				continue;
			}
		}
    //按照优先级排序
		AnnotationAwareOrderComparator.sort(elements);
		//获取所有的组件类名
		String[] classNames = elements.stream().map(e -> e.name).toArray(String[]::new);

		return classNames;
	}
	}
```

org.springframework.cloud.bootstrap.BootstrapApplicationListener#onApplicationEvent

```java
public void onApplicationEvent(ApplicationEnvironmentPreparedEvent event) {
   ConfigurableEnvironment environment = event.getEnvironment();
   if (!environment.getProperty("spring.cloud.bootstrap.enabled", Boolean.class,
         true)) {
      return;
   }
   // don't listen to events in a bootstrap context
   if (environment.getPropertySources().contains(BOOTSTRAP_PROPERTY_SOURCE_NAME)) {
      return;
   }
   ConfigurableApplicationContext context = null;
   String configName = environment
         .resolvePlaceholders("${spring.cloud.bootstrap.name:bootstrap}");
   for (ApplicationContextInitializer<?> initializer : event.getSpringApplication()
         .getInitializers()) {
      if (initializer instanceof ParentContextApplicationContextInitializer) {
         context = findBootstrapContext(
               (ParentContextApplicationContextInitializer) initializer,
               configName);
      }
   }
   if (context == null) {
      context = bootstrapServiceContext(environment, event.getSpringApplication(),
            configName);
      event.getSpringApplication()
            .addListeners(new CloseContextOnFailureApplicationListener(context));
   }
	 // 从springcloud工厂里拿出ApplicationContextInitializer.class，设置springboot的Initializers里，
   apply(context, event.getSpringApplication(), environment);
}
```

org.springframework.cloud.bootstrap.BootstrapApplicationListener#apply

```java
private void apply(ConfigurableApplicationContext context,
      SpringApplication application, ConfigurableEnvironment environment) {
   if (application.getAllSources().contains(BootstrapMarkerConfiguration.class)) {
      return;
   }
   application.addPrimarySources(Arrays.asList(BootstrapMarkerConfiguration.class));
   @SuppressWarnings("rawtypes")
   Set target = new LinkedHashSet<>(application.getInitializers());
   // 从springcloud工厂里拿出ApplicationContextInitializer.class（主要是PropertySourceBootstrapConfiguration）放入initializers
   target.addAll(
         getOrderedBeansOfType(context, ApplicationContextInitializer.class));
   application.setInitializers(target);
   addBootstrapDecryptInitializer(application);
}
```

此类会将springcloud中bootstrap上下文需要加载的组件注入到IOC容器，其spring.factories配置文件中的配置key为org.springframework.cloud.bootstrap.BootstrapConfiguration。



```java
@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(PropertySourceBootstrapProperties.class)
public class PropertySourceBootstrapConfiguration implements
      ApplicationContextInitializer<ConfigurableApplicationContext>, Ordered {

   /**
    * Bootstrap property source name.
    */
   public static final String BOOTSTRAP_PROPERTY_SOURCE_NAME = BootstrapApplicationListener.BOOTSTRAP_PROPERTY_SOURCE_NAME
         + "Properties";

   private static Log logger = LogFactory
         .getLog(PropertySourceBootstrapConfiguration.class);

   private int order = Ordered.HIGHEST_PRECEDENCE + 10;

   @Autowired(required = false)
  // 注入PropertySourceLocator，例如spring cloud config，nacosPropertySourceLocator
   private List<PropertySourceLocator> propertySourceLocators = new ArrayList<>();
   
   	@Override
	public void initialize(ConfigurableApplicationContext applicationContext) {
		List<PropertySource<?>> composite = new ArrayList<>();
		AnnotationAwareOrderComparator.sort(this.propertySourceLocators);
		boolean empty = true;
		ConfigurableEnvironment environment = applicationContext.getEnvironment();
		for (PropertySourceLocator locator : this.propertySourceLocators) {
			Collection<PropertySource<?>> source = locator.locateCollection(environment);
			if (source == null || source.size() == 0) {
				continue;
			}
			List<PropertySource<?>> sourceList = new ArrayList<>();
			for (PropertySource<?> p : source) {
				if (p instanceof EnumerablePropertySource) {
					EnumerablePropertySource<?> enumerable = (EnumerablePropertySource<?>) p;
					sourceList.add(new BootstrapPropertySource<>(enumerable));
				}
				else {
					sourceList.add(new SimpleBootstrapPropertySource(p));
				}
			}
			logger.info("Located property source: " + sourceList);
			composite.addAll(sourceList);
			empty = false;
		}
		if (!empty) {
			MutablePropertySources propertySources = environment.getPropertySources();
			String logConfig = environment.resolvePlaceholders("${logging.config:}");
			LogFile logFile = LogFile.get(environment);
			for (PropertySource<?> p : environment.getPropertySources()) {
				if (p.getName().startsWith(BOOTSTRAP_PROPERTY_SOURCE_NAME)) {
					propertySources.remove(p.getName());
				}
			}
			insertPropertySources(propertySources, composite);
			reinitializeLoggingSystem(environment, logConfig, logFile);
			setLogLevels(applicationContext, environment);
			handleIncludedProfiles(environment);
		}
	}
  
	private void insertPropertySources(MutablePropertySources propertySources,
			List<PropertySource<?>> composite) {
		MutablePropertySources incoming = new MutablePropertySources();
		List<PropertySource<?>> reversedComposite = new ArrayList<>(composite);
		// Reverse the list so that when we call addFirst below we are maintaining the
		// same order of PropertySources
		// Wherever we call addLast we can use the order in the List since the first item
		// will end up before the rest
		Collections.reverse(reversedComposite);
		for (PropertySource<?> p : reversedComposite) {
			incoming.addFirst(p);
		}
		PropertySourceBootstrapProperties remoteProperties = new PropertySourceBootstrapProperties();
		Binder.get(environment(incoming)).bind("spring.cloud.config",
				Bindable.ofInstance(remoteProperties));
		if (!remoteProperties.isAllowOverride() || (!remoteProperties.isOverrideNone()
				&& remoteProperties.isOverrideSystemProperties())) {
			for (PropertySource<?> p : reversedComposite) {
				propertySources.addFirst(p);
			}
			return;
		}
		if (remoteProperties.isOverrideNone()) {
			for (PropertySource<?> p : composite) {
				propertySources.addLast(p);
			}
			return;
		}
		if (propertySources.contains(SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME)) {
			if (!remoteProperties.isOverrideSystemProperties()) {
				for (PropertySource<?> p : reversedComposite) {
					propertySources.addAfter(SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME, p);
				}
			}
			else {
				for (PropertySource<?> p : composite) {
					propertySources.addBefore(SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME, p);
				}
			}
		}
		else {
			for (PropertySource<?> p : composite) {
				propertySources.addLast(p);
			}
		}
	}
  
}
```

![image-20210807205630396](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20210807205630396.png)



![image-20211216163842249](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20211216163842249.png)

ribbon applicationContext是由springclientFactory生成的

```java
public class SpringClientFactory extends NamedContextFactory<RibbonClientSpecification> 
public class FeignContext extends NamedContextFactory<FeignClientSpecification> 
public class SeataFeignContext extends FeignContext 
```

引入springcloud config：

springboot run->envprepared event->springcloud application run -> configure class BootstrapImportSelectorConfiguration.class ->import PropertySourceBootstrapConfiguration class and set to springboot initializers -> springboot apply initializers -> import spring cloud config

## 参考

http://www.ligen.pro/2018/01/17/@ConfigurationProperties源码解析/

https://cloud.tencent.com/developer/article/1403379