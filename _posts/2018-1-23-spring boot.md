---
ddate: 2018-1-23
layout: default

title: spring boot

---

# spring boot

## spring
DI（依赖注入IOC）

AOP（面向切面编程）

把有一些类注解，实例一次，放入ioc容器

通过autowired等注解，从ioc容器里拿实例

## spring boot

创建一个基于spring的应用简单

自动配置

零xml配置

application.properties是spring boot默认的配置文件，spring boot默认会在以下两个路径搜索并加载这个文件

src\main\resources

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
      ConfigurableEnvironment environment = prepareEnvironment(listeners,
            applicationArguments);
      configureIgnoreBeanInfo(environment);
      Banner printedBanner = printBanner(environment);
      context = createApplicationContext();
      exceptionReporters = getSpringFactoriesInstances(
            SpringBootExceptionReporter.class,
            new Class[] { ConfigurableApplicationContext.class }, context);
      prepareContext(context, environment, listeners, applicationArguments,
            printedBanner);
      // 创建spring容器，和web服务器
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