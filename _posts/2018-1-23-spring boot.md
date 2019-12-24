---
layout: default

title: spring boot

---

## spring boot

### spring
DI（依赖注入IOC）

AOP（面向切面编程）

把有一些类注解，实例一次，放入ioc容器

通过autowired等注解，从ioc容器里拿实例

### spring boot

创建一个基于spring的应用简单

自动配置

零xml配置

application.properties是spring boot默认的配置文件，spring boot默认会在以下两个路径搜索并加载这个文件

src\main\resources

src\main\resources\config

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

### 程序开始

SpringApplication.run（），进行自动配置

#### SpringApplication构造函数

org.springframework.boot.SpringApplication#SpringApplication(org.springframework.core.io.ResourceLoader, java.lang.Class<?>...)

```java
public SpringApplication(ResourceLoader resourceLoader, Class<?>... primarySources) {
		this.resourceLoader = resourceLoader;
		Assert.notNull(primarySources, "PrimarySources must not be null");
		this.primarySources = new LinkedHashSet<>(Arrays.asList(primarySources));
		this.webApplicationType = deduceWebApplicationType();
    // 从spring.factories找到org.springframework.context.ApplicationContextInitializer实现类
		setInitializers((Collection) getSpringFactoriesInstances(
				ApplicationContextInitializer.class));
    // 从spring.factories找到org.springframework.context.ApplicationListener实现类
		setListeners((Collection) getSpringFactoriesInstances(ApplicationListener.class));
		this.mainApplicationClass = deduceMainApplicationClass();
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
      // 创建spring容器
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

##### 创建spring容器

根据import注解，解析META-INF/spring.factories文件，导入第三方组件的启动类（org.springframework.boot.autoconfigure.EnableAutoConfiguration）

@SpringBootApplication->@EnableAutoConfiguration->@Import(AutoConfigurationImportSelector.class)

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

### 

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






