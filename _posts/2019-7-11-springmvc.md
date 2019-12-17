---
layout: default

title: springmvc

---

# springmvc

## tomcat触发

org.apache.catalina.core.StandardContext#startInternal

org.apache.catalina.core.StandardContext#listenerStart

```java
for (int i = 0; i < instances.length; i++) {
	listener.contextInitialized(event);
}
```

## xml方式spring ioc容器初始化（根上下文）

**Spring Framework本身没有Web功能，Spring MVC使用WebApplicationContext接口扩展ApplicationContext，使得拥有web功能，WebApplicationContext接口默认的实现是XmlWebApplicationContext**

![image-20191217112839316](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191217112839316.png)

application-context.xml配置context等全局信息，包括设置servlet和servlet-mapping、filter信息

mvc.xml配置DispatcherServlet信息

```xml
<web-app>

    <listener>
      	// context相关监听器，处理初始化和销毁事件
        <listener-class>org.springframework.web.context.ContextLoaderListener</listener-class>
    </listener>

    <context-param>
        <param-name>contextConfigLocation</param-name>
        <param-value>/WEB-INF/app-context.xml</param-value>
    </context-param>

    <servlet>
        <servlet-name>app</servlet-name>
        <servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>
        <init-param>
            <param-name>contextConfigLocation</param-name>
            <param-value></param-value>
        </init-param>
        <load-on-startup>1</load-on-startup>
    </servlet>

    <servlet-mapping>
        <servlet-name>app</servlet-name>
        <url-pattern>/app/*</url-pattern>
    </servlet-mapping>

</web-app>

```

```java
public class ContextLoaderListener extends ContextLoader implements ServletContextListener {

	public ContextLoaderListener() {
	}

	public ContextLoaderListener(WebApplicationContext context) {
		super(context);
	}


	/**
	 * Initialize the root web application context.
	 */
	@Override
	public void contextInitialized(ServletContextEvent event) {
		initWebApplicationContext(event.getServletContext());
	}


	/**
	 * Close the root web application context.
	 */
	@Override
	public void contextDestroyed(ServletContextEvent event) {
		closeWebApplicationContext(event.getServletContext());
		ContextCleanupListener.cleanupAttributes(event.getServletContext());
	}

}
```

```java
public WebApplicationContext initWebApplicationContext(ServletContext servletContext) {
  // 在整个web应用中，只能有一个根上下文，判断ServletContext中是否已经有根上下文 
  if (servletContext.getAttribute(WebApplicationContext.ROOT_WEB_APPLICATION_CONTEXT_ATTRIBUTE) != null) {
      throw new IllegalStateException(
            "Cannot initialize context because there is already a root application context present - " +
            "check whether you have multiple ContextLoader* definitions in your web.xml!");
   }

   Log logger = LogFactory.getLog(ContextLoader.class);
   servletContext.log("Initializing Spring root WebApplicationContext");
   if (logger.isInfoEnabled()) {
      logger.info("Root WebApplicationContext: initialization started");
   }
   long startTime = System.currentTimeMillis();

   try {
      // Store context in local instance variable, to guarantee that
      // it is available on ServletContext shutdown.
      if (this.context == null) {
        //判空 (以注解方式配置时非空)
         this.context = createWebApplicationContext(servletContext);
      }
      if (this.context instanceof ConfigurableWebApplicationContext) {
         ConfigurableWebApplicationContext cwac = (ConfigurableWebApplicationContext) this.context;
         if (!cwac.isActive()) {
            // The context has not yet been refreshed -> provide services such as
            // setting the parent context, setting the application context id, etc
            if (cwac.getParent() == null) {
               // The context instance was injected without an explicit parent ->
               // determine parent for root web application context, if any.
               // 根上下文也有双亲上下文
               ApplicationContext parent = loadParentContext(servletContext);
               cwac.setParent(parent);
            }
           	// 配置根上下文
            configureAndRefreshWebApplicationContext(cwac, servletContext);
         }
      }
// 将applicationContext设置到servletContext中
     servletContext.setAttribute(WebApplicationContext.ROOT_WEB_APPLICATION_CONTEXT_ATTRIBUTE, this.context);

      ClassLoader ccl = Thread.currentThread().getContextClassLoader();
      if (ccl == ContextLoader.class.getClassLoader()) {
         currentContext = this.context;
      }
      else if (ccl != null) {
         currentContextPerThread.put(ccl, this.context);
      }

      if (logger.isDebugEnabled()) {
         logger.debug("Published root WebApplicationContext as ServletContext attribute with name [" +
               WebApplicationContext.ROOT_WEB_APPLICATION_CONTEXT_ATTRIBUTE + "]");
      }
      if (logger.isInfoEnabled()) {
         long elapsedTime = System.currentTimeMillis() - startTime;
         logger.info("Root WebApplicationContext: initialization completed in " + elapsedTime + " ms");
      }

      return this.context;
   }
   catch (RuntimeException ex) {
      logger.error("Context initialization failed", ex);
      servletContext.setAttribute(WebApplicationContext.ROOT_WEB_APPLICATION_CONTEXT_ATTRIBUTE, ex);
      throw ex;
   }
   catch (Error err) {
      logger.error("Context initialization failed", err);
      servletContext.setAttribute(WebApplicationContext.ROOT_WEB_APPLICATION_CONTEXT_ATTRIBUTE, err);
      throw err;
   }
}
```

```java
protected WebApplicationContext createWebApplicationContext(ServletContext sc) {
   Class<?> contextClass = determineContextClass(sc);
   if (!ConfigurableWebApplicationContext.class.isAssignableFrom(contextClass)) {
      throw new ApplicationContextException("Custom context class [" + contextClass.getName() +
            "] is not of type [" + ConfigurableWebApplicationContext.class.getName() + "]");
   }
   return (ConfigurableWebApplicationContext) BeanUtils.instantiateClass(contextClass);
}
```

从initParameter的contextClass参数或者ContextLoader.properties文件中（org.springframework.web.context.WebApplicationContext=org.springframework.web.context.support.XmlWebApplicationContext）获取contextClassName

```java
protected Class<?> determineContextClass(ServletContext servletContext) {
   // 根据web.xml的配置决定WebApplicationContext
   String contextClassName = servletContext.getInitParameter(CONTEXT_CLASS_PARAM);
   if (contextClassName != null) {
      try {
         return ClassUtils.forName(contextClassName, ClassUtils.getDefaultClassLoader());
      }
      catch (ClassNotFoundException ex) {
         throw new ApplicationContextException(
               "Failed to load custom context class [" + contextClassName + "]", ex);
      }
   }
   else {
      // 根据配置文件ContextLoader.properties决定WebApplicationContext
      contextClassName = defaultStrategies.getProperty(WebApplicationContext.class.getName());
      try {
         return ClassUtils.forName(contextClassName, ContextLoader.class.getClassLoader());
      }
      catch (ClassNotFoundException ex) {
         throw new ApplicationContextException(
               "Failed to load default context class [" + contextClassName + "]", ex);
      }
   }
}
```

```java
protected void configureAndRefreshWebApplicationContext(ConfigurableWebApplicationContext wac, ServletContext sc) {
   if (ObjectUtils.identityToString(wac).equals(wac.getId())) {
      // The application context id is still set to its original default value
      // -> assign a more useful id based on available information
      String idParam = sc.getInitParameter(CONTEXT_ID_PARAM);
      if (idParam != null) {
         wac.setId(idParam);
      }
      else {
         // Generate default id...
         wac.setId(ConfigurableWebApplicationContext.APPLICATION_CONTEXT_ID_PREFIX +
               ObjectUtils.getDisplayString(sc.getContextPath()));
      }
   }

   wac.setServletContext(sc);
   String configLocationParam = sc.getInitParameter(CONFIG_LOCATION_PARAM);
   if (configLocationParam != null) {
      wac.setConfigLocation(configLocationParam);
   }

   // The wac environment's #initPropertySources will be called in any case when the context
   // is refreshed; do it eagerly here to ensure servlet property sources are in place for
   // use in any post-processing or initialization that occurs below prior to #refresh
   ConfigurableEnvironment env = wac.getEnvironment();
   if (env instanceof ConfigurableWebEnvironment) {
      ((ConfigurableWebEnvironment) env).initPropertySources(sc, null);
   }
	 // 根据xml定制上下文（初始化ApplicationContextInitializer接口的实现）
   customizeContext(sc, wac);
   // spring容器初始化
   wac.refresh();
}
```

## mvc容器diapatcherServlet的初始化（子上下文）

### tomcat端触发

org.apache.catalina.core.StandardWrapper#loadServlet

org.apache.catalina.core.StandardWrapper#initServlet

servlet.init(facade);

### servlet端

由ContextLoaderListener首先启动的上下文为根上下文，该上下文是与ServletContext相伴而生的，在根上下文的基础上，Spring MVC对应持有的一个用来管理控制器需要的对象的子上下文

**ContextLoaderListener加载的时候已经创建了WebApplicationContext实例，而在这里是对这个实例的进一步补充初始化**

![image-20191217134337828](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191217134337828.png)

org.springframework.web.servlet.HttpServletBean#init

org.springframework.web.servlet.FrameworkServlet#initServletBean

```java
public final void init() throws ServletException {
   if (logger.isDebugEnabled()) {
      logger.debug("Initializing servlet '" + getServletName() + "'");
   }

   // Set bean properties from init parameters.
  // 读取web.xml中DispatchServlet定义中的<init-param>，对Bean属性进行配置
   PropertyValues pvs = new ServletConfigPropertyValues(getServletConfig(), this.requiredProperties);
   if (!pvs.isEmpty()) {
      try {
        // 生成一个BeanWrapper，将当前的这个Servlet类转化为一个BeanWrapper，从而能够以Spring的方式来对init-param的值进行注入
         BeanWrapper bw = PropertyAccessorFactory.forBeanPropertyAccess(this);
         ResourceLoader resourceLoader = new ServletContextResourceLoader(getServletContext());
         bw.registerCustomEditor(Resource.class, new ResourceEditor(resourceLoader, getEnvironment()));
         initBeanWrapper(bw);
         bw.setPropertyValues(pvs, true);
      }
      catch (BeansException ex) {
         if (logger.isErrorEnabled()) {
            logger.error("Failed to set bean properties on servlet '" + getServletName() + "'", ex);
         }
         throw ex;
      }
   }

   // Let subclasses do whatever initialization they like.
  // 创建子容器
   initServletBean();

   if (logger.isDebugEnabled()) {
      logger.debug("Servlet '" + getServletName() + "' configured successfully");
   }
}
```

```java
protected final void initServletBean() throws ServletException {
   getServletContext().log("Initializing Spring FrameworkServlet '" + getServletName() + "'");
   if (this.logger.isInfoEnabled()) {
      this.logger.info("FrameworkServlet '" + getServletName() + "': initialization started");
   }
   long startTime = System.currentTimeMillis();

   try {
      this.webApplicationContext = initWebApplicationContext();
      initFrameworkServlet();
   }
   catch (ServletException | RuntimeException ex) {
      this.logger.error("Context initialization failed", ex);
      throw ex;
   }

   if (this.logger.isInfoEnabled()) {
      long elapsedTime = System.currentTimeMillis() - startTime;
      this.logger.info("FrameworkServlet '" + getServletName() + "': initialization completed in " +
            elapsedTime + " ms");
   }
}
```



DispatcherServlet创建WebApplicationContext作为springmvc的上下文 并将ContextLoadListener创建的上下文设置为自身的parent

org.springframework.web.servlet.FrameworkServlet#initWebApplicationContext

```java
protected WebApplicationContext initWebApplicationContext() {
  // 这里调用WebApplicationContextUtils静态类来从ServletContext中得到根上下文，使用这个根上下文作为当前MVC上下文的双亲上下文。
   WebApplicationContext rootContext =
         WebApplicationContextUtils.getWebApplicationContext(getServletContext());
   WebApplicationContext wac = null;

   if (this.webApplicationContext != null) {
      // A context instance was injected at construction time -> use it
      wac = this.webApplicationContext;
      if (wac instanceof ConfigurableWebApplicationContext) {
         ConfigurableWebApplicationContext cwac = (ConfigurableWebApplicationContext) wac;
         if (!cwac.isActive()) {
            // The context has not yet been refreshed -> provide services such as
            // setting the parent context, setting the application context id, etc
            if (cwac.getParent() == null) {
               // The context instance was injected without an explicit parent -> set
               // the root application context (if any; may be null) as the parent
               cwac.setParent(rootContext);
            }
            configureAndRefreshWebApplicationContext(cwac);
         }
      }
   }
   if (wac == null) {
      // No context instance was injected at construction time -> see if one
      // has been registered in the servlet context. If one exists, it is assumed
      // that the parent context (if any) has already been set and that the
      // user has performed any initialization such as setting the context id
      wac = findWebApplicationContext();
   }
   if (wac == null) {
      // No context instance is defined for this servlet -> create a local one
     // 在ServletContext没有context实例，所以需要创建一个WebApplicationContext，以根上下文为双亲下文创建
      wac = createWebApplicationContext(rootContext);
   }

   if (!this.refreshEventReceived) {
      // Either the context is not a ConfigurableApplicationContext with refresh
      // support or the context injected at construction time had already been
      // refreshed -> trigger initial onRefresh manually here.
      onRefresh(wac);
   }

   if (this.publishContext) {
      // Publish the context as a servlet context attribute.
      String attrName = getServletContextAttributeName();
      getServletContext().setAttribute(attrName, wac);
      if (this.logger.isDebugEnabled()) {
         this.logger.debug("Published WebApplicationContext of servlet '" + getServletName() +
               "' as ServletContext attribute with name [" + attrName + "]");
      }
   }

   return wac;
}
```

org.springframework.web.servlet.DispatcherServlet#onRefresh

```java
	protected void onRefresh(ApplicationContext context) {
		initStrategies(context);
	}
```

```java
protected void initStrategies(ApplicationContext context) {
		initMultipartResolver(context);
		initLocaleResolver(context);
		initThemeResolver(context);
  	// 初始化不同的handlermapping
		initHandlerMappings(context);
    // 初始化不同的handlerAdpters，逻辑同上，如果没有adapter注入，使用DispatcherServlet.properties文件里是（org.springframework.web.servlet.HandlerAdapter=org.springframework.web.servlet.mvc.HttpRequestHandlerAdapter,\org.springframework.web.servlet.mvc.SimpleControllerHandlerAdapter,\org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerAdapter）

		initHandlerAdapters(context);
		initHandlerExceptionResolvers(context);
		initRequestToViewNameTranslator(context);
		initViewResolvers(context);
		initFlashMapManager(context);
	}
```

加了<mvc:annotation-driven />注解会加载如下bean

![image-20191217162033594](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191217162033594.png)

```java
	private void initHandlerMappings(ApplicationContext context) {
		this.handlerMappings = null;

		if (this.detectAllHandlerMappings) {
      // 从srping容器里找实现HandlerMapping.class的bean，可以自己实现该handlerMapping
			// Find all HandlerMappings in the ApplicationContext, including ancestor contexts.
			Map<String, HandlerMapping> matchingBeans =
					BeanFactoryUtils.beansOfTypeIncludingAncestors(context, HandlerMapping.class, true, false);
			if (!matchingBeans.isEmpty()) {
				this.handlerMappings = new ArrayList<>(matchingBeans.values());
				// We keep HandlerMappings in sorted order.
				AnnotationAwareOrderComparator.sort(this.handlerMappings);
			}
		}
		else {
			try {
				HandlerMapping hm = context.getBean(HANDLER_MAPPING_BEAN_NAME, HandlerMapping.class);
				this.handlerMappings = Collections.singletonList(hm);
			}
			catch (NoSuchBeanDefinitionException ex) {
				// Ignore, we'll add a default HandlerMapping later.
			}
		}

		// Ensure we have at least one HandlerMapping, by registering
		// a default HandlerMapping if no other mappings are found.
		if (this.handlerMappings == null) {
      // 如果容器里找不到handlerMappings，即xml里没有配置handlerMapping
      // 从DispatcherServlet.properties读取handerMapping并放入spring容器里
			this.handlerMappings = getDefaultStrategies(context, HandlerMapping.class);
			if (logger.isDebugEnabled()) {
				logger.debug("No HandlerMappings found in servlet '" + getServletName() + "': using default");
			}
		}
	}
```

通过文件初始化handlerMapping

定义在org/springframework/web/servlet/DispatcherServlet.properties文件中

```java
org.springframework.web.servlet.HandlerMapping=org.springframework.web.servlet.handler.BeanNameUrlHandlerMapping,\
   org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping
```

**两种主要的handlerMapping，RequestMappingHandlerMapping，SimpleUrlHandlerMapping**

```
The two main HandlerMapping implementations are RequestMappingHandlerMapping (which supports @RequestMapping annotated methods) and SimpleUrlHandlerMapping (which maintains explicit registrations of URI path patterns to handlers).


<bean id="urlMapping"
        class="org.springframework.web.servlet.handler.SimpleUrlHandlerMapping">
    <property name="interceptors">
        <list>
            <ref bean="localeChangeInterceptor"/>
        </list>
    </property>
    <property name="mappings">
        <value>/**/*.view=someController</value>
    </property>
</bean>
```



DispatcherServlet类，加载DispatcherServlet.properties文件，初始化defaultStrategies

```java
static {
		// Load default strategy implementations from properties file.
		// This is currently strictly internal and not meant to be customized
		// by application developers.
		try {
			ClassPathResource resource = new ClassPathResource(DEFAULT_STRATEGIES_PATH, DispatcherServlet.class);
			defaultStrategies = PropertiesLoaderUtils.loadProperties(resource);
		}
		catch (IOException ex) {
			throw new IllegalStateException("Could not load '" + DEFAULT_STRATEGIES_PATH + "': " + ex.getMessage());
		}
	}
```



有三种方式注册handler

```java
1. 
@Component
Implements Controller

2.
@Component
implements HttpRequestHandler

3.
@Controller
```



Spring MVC提供了许多HandlerMapping的实现，默认使用的是BeanNameUrlHandlerMapping，可以根据Bean的name属性映射到URL中

HandlerMapping继承的ApplicationObjectSupport实现了ApplicationContextAware，spring的bean后置处理器，会调用他的setApplicationContext

```java
if (bean instanceof ApplicationContextAware) {
   ((ApplicationContextAware) bean).setApplicationContext(this.applicationContext);
}
```

setApplicationContext里会调用子类的initApplicationContext

```java
@Override
public final void setApplicationContext(@Nullable ApplicationContext context) throws BeansException {
   if (context == null && !isContextRequired()) {
      // Reset internal context state.
      this.applicationContext = null;
      this.messageSourceAccessor = null;
   }
   else if (this.applicationContext == null) {
      // Initialize with passed-in context.
      if (!requiredContextClass().isInstance(context)) {
         throw new ApplicationContextException(
               "Invalid application context: needs to be of type [" + requiredContextClass().getName() + "]");
      }
      this.applicationContext = context;
      this.messageSourceAccessor = new MessageSourceAccessor(context);
      initApplicationContext(context);
   }
   else {
      // Ignore reinitialization if same context passed in.
      if (this.applicationContext != context) {
         throw new ApplicationContextException(
               "Cannot reinitialize with different application context: current one is [" +
               this.applicationContext + "], passed-in one is [" + context + "]");
      }
   }
}
```



```java
public abstract class AbstractDetectingUrlHandlerMapping extends AbstractUrlHandlerMapping {
  	public void initApplicationContext() throws ApplicationContextException {
      // 设置拦截器
      super.initApplicationContext();
      detectHandlers();
    }
  
  // 注册url和handler bean的关联
  protected void detectHandlers() throws BeansException {
		ApplicationContext applicationContext = obtainApplicationContext();
		if (logger.isDebugEnabled()) {
			logger.debug("Looking for URL mappings in application context: " + applicationContext);
		}
		String[] beanNames = (this.detectHandlersInAncestorContexts ?
				BeanFactoryUtils.beanNamesForTypeIncludingAncestors(applicationContext, Object.class) :
				applicationContext.getBeanNamesForType(Object.class));

		// Take any bean name that we can determine URLs for.
		for (String beanName : beanNames) {
      // 找到bean名开头是"/"的bean
			String[] urls = determineUrlsForHandler(beanName);
			if (!ObjectUtils.isEmpty(urls)) {
				// URL paths found: Let's consider it a handler.
        // 把url和对应的bean注册到this.handlerMap，bean即handler
				registerHandler(urls, beanName);
			}
			else {
				if (logger.isDebugEnabled()) {
					logger.debug("Rejected bean name '" + beanName + "': no URL paths identified");
				}
			}
		}
	}
}


```

#### BeanNameUrlHandlerMapping

```java

public class BeanNameUrlHandlerMapping extends AbstractDetectingUrlHandlerMapping {

	@Override
 	// 找到beanName开头是"/"或者别名里开头是"/"的bean
	protected String[] determineUrlsForHandler(String beanName) {
		List<String> urls = new ArrayList<>();
		if (beanName.startsWith("/")) {
			urls.add(beanName);
		}
		String[] aliases = obtainApplicationContext().getAliases(beanName);
		for (String alias : aliases) {
			if (alias.startsWith("/")) {
				urls.add(alias);
			}
		}
		return StringUtils.toStringArray(urls);
	}
}
```

#### BeanNameUrlHandlerMapping

```java
public class RequestMappingHandlerMapping extends RequestMappingInfoHandlerMapping
      implements MatchableHandlerMapping, EmbeddedValueResolverAware {
  
  	public void afterPropertiesSet() {
      this.config = new RequestMappingInfo.BuilderConfiguration();
      this.config.setUrlPathHelper(getUrlPathHelper());
      this.config.setPathMatcher(getPathMatcher());
      this.config.setSuffixPatternMatch(this.useSuffixPatternMatch);
      this.config.setTrailingSlashMatch(this.useTrailingSlashMatch);
      this.config.setRegisteredSuffixPatternMatch(this.useRegisteredSuffixPatternMatch);
      this.config.setContentNegotiationManager(getContentNegotiationManager());

      super.afterPropertiesSet();
    }
}
```



```java
public abstract class AbstractHandlerMethodMapping<T> extends AbstractHandlerMapping implements InitializingBean {
  
	org.springframework.web.servlet.handler.AbstractHandlerMethodMapping#afterPropertiesSet->org.springframework.web.servlet.handler.AbstractHandlerMethodMapping#initHandlerMethods

	将uri mapping到方法
    
    protected void initHandlerMethods() {
		if (logger.isDebugEnabled()) {
			logger.debug("Looking for request mappings in application context: " + getApplicationContext());
		}
    // 获取spring容器里的所有bean
		String[] beanNames = (this.detectHandlerMethodsInAncestorContexts ?
				BeanFactoryUtils.beanNamesForTypeIncludingAncestors(obtainApplicationContext(), Object.class) :
				obtainApplicationContext().getBeanNamesForType(Object.class));

		for (String beanName : beanNames) {
			if (!beanName.startsWith(SCOPED_TARGET_NAME_PREFIX)) {
				Class<?> beanType = null;
				try {
					beanType = obtainApplicationContext().getType(beanName);
				}
				catch (Throwable ex) {
					// An unresolvable bean type, probably from a lazy bean - let's ignore it.
					if (logger.isDebugEnabled()) {
						logger.debug("Could not resolve target class for bean with name '" + beanName + "'", ex);
					}
				}
        // 找到有Controller.class和RequestMapping.class注解的bean
				if (beanType != null && isHandler(beanType)) {
          // 找到类里所有RequestMapping注解的方法，映射uri和方法信息
					detectHandlerMethods(beanName);
				}
			}
		}
		handlerMethodsInitialized(getHandlerMethods());
	}
}
```

将url和bean method注册到urlLookup

```java
public void register(T mapping, Object handler, Method method) {
			this.readWriteLock.writeLock().lock();
			try {
				HandlerMethod handlerMethod = createHandlerMethod(handler, method);
				assertUniqueMethodMapping(handlerMethod, mapping);

				if (logger.isInfoEnabled()) {
					logger.info("Mapped \"" + mapping + "\" onto " + handlerMethod);
				}
				this.mappingLookup.put(mapping, handlerMethod);

				List<String> directUrls = getDirectUrls(mapping);
				for (String url : directUrls) {
					this.urlLookup.add(url, mapping);
				}

				String name = null;
				if (getNamingStrategy() != null) {
					name = getNamingStrategy().getName(handlerMethod, mapping);
					addMappingName(name, handlerMethod);
				}

				CorsConfiguration corsConfig = initCorsConfiguration(handler, method, mapping);
				if (corsConfig != null) {
					this.corsLookup.put(handlerMethod, corsConfig);
				}

				this.registry.put(mapping, new MappingRegistration<>(mapping, handlerMethod, directUrls, name));
			}
			finally {
				this.readWriteLock.writeLock().unlock();
			}
		}
```



HandlerMapping的初始化过程主要分成两部分，通过initInterceptors()方法将SimpleUrlHandlerMapping中定义的interceptors包装成HandlerInterceptor对象保存在adaptedInterceptors数组中，同时通过registerHandlers()方法将SimpleHandlerMapping中定义的mappings（即URL与Handler的映射）注册到handlerMap集合中。



![image-20191217104942808](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191217104942808.png)

![image-20191217105507248](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191217105507248.png)



## 不使用web.xml，引入springmvc

#### 重写onStartup方法，只创建1个上下文，不重写则会有2个上下文

```java
import org.springframework.web.WebApplicationInitializer;

public class MyWebApplicationInitializer implements WebApplicationInitializer {

    @Override
    public void onStartup(ServletContext container) {
        XmlWebApplicationContext appContext = new XmlWebApplicationContext();
        appContext.setConfigLocation("/WEB-INF/spring/dispatcher-config.xml");

        ServletRegistration.Dynamic registration = container.addServlet("dispatcher", new DispatcherServlet(appContext));
        registration.setLoadOnStartup(1);
        registration.addMapping("/");
    }
}
```

```java
public class MyWebApplicationInitializer implements WebApplicationInitializer {

    @Override
    public void onStartup(ServletContext servletCxt) {

        // Load Spring web application configuration
        AnnotationConfigWebApplicationContext ac = new AnnotationConfigWebApplicationContext();
        ac.register(AppConfig.class);
        ac.refresh();

        // Create and register the DispatcherServlet
      	// 将spring容器复制给servlet
        DispatcherServlet servlet = new DispatcherServlet(ac);
        ServletRegistration.Dynamic registration = servletCxt.addServlet("app", servlet);
        registration.setLoadOnStartup(1);
        registration.addMapping("/app/*");
    }
}
```

使用ServletContainerInitializer接口导入tomcat

### spring端

spring-web工程下有

META-INF/services/javax.servlet.ServletContainerInitializer文件，文件内容为

```java
org.springframework.web.SpringServletContainerInitializer
```



```java
@HandlesTypes(WebApplicationInitializer.class)
public class SpringServletContainerInitializer implements ServletContainerInitializer {

	@Override
	public void onStartup(@Nullable Set<Class<?>> webAppInitializerClasses, ServletContext servletContext)
			throws ServletException {

		List<WebApplicationInitializer> initializers = new LinkedList<>();

		if (webAppInitializerClasses != null) {
			for (Class<?> waiClass : webAppInitializerClasses) {
				// Be defensive: Some servlet containers provide us with invalid classes,
				// no matter what @HandlesTypes says...
				if (!waiClass.isInterface() && !Modifier.isAbstract(waiClass.getModifiers()) &&
						WebApplicationInitializer.class.isAssignableFrom(waiClass)) {
					try {
						initializers.add((WebApplicationInitializer)
								ReflectionUtils.accessibleConstructor(waiClass).newInstance());
					}
					catch (Throwable ex) {
						throw new ServletException("Failed to instantiate WebApplicationInitializer class", ex);
					}
				}
			}
		}

		if (initializers.isEmpty()) {
			servletContext.log("No Spring WebApplicationInitializer types detected on classpath");
			return;
		}

		servletContext.log(initializers.size() + " Spring WebApplicationInitializers detected on classpath");
		AnnotationAwareOrderComparator.sort(initializers);
		for (WebApplicationInitializer initializer : initializers) {
			initializer.onStartup(servletContext);
		}
	}

}
```

#### **同xml一样，也有两个上下文**

流程和xml一样

AbstractDispatcherServletInitializer#onStartup

```java
@Override
public void onStartup(ServletContext servletContext) throws ServletException {
	super.onStartup(servletContext);
	// 创建子上下文
	registerDispatcherServlet(servletContext);
}

protected void registerDispatcherServlet(ServletContext servletContext) {
	// Servlet名称 一般用系统默认的即可，否则自己复写此方法也成
	String servletName = getServletName();
	Assert.hasLength(servletName, "getServletName() must not return null or empty");
	
	// 创建web的子容器。创建的代码和上面差不多，也是使用调用者提供的配置文件，创建AnnotationConfigWebApplicationContext.  备注：此处不可能为null哦
	WebApplicationContext servletAppContext = createServletApplicationContext();
	Assert.notNull(servletAppContext, "createServletApplicationContext() must not return null");
	
	//创建DispatcherServlet，并且把子容器传进去了。其实就是new一个出来，最后加到容器里，就能够执行一些init初始化方法了~
	FrameworkServlet dispatcherServlet = createDispatcherServlet(servletAppContext);
	Assert.notNull(dispatcherServlet, "createDispatcherServlet(WebApplicationContext) must not return null");
	//同样的 getServletApplicationContextInitializers()一般也为null即可
	dispatcherServlet.setContextInitializers(getServletApplicationContextInitializers());
	
	//注册servlet到web容器里面，这样就可以接收请求了
	ServletRegistration.Dynamic registration = servletContext.addServlet(servletName, dispatcherServlet);
	if (registration == null) {
		throw new IllegalStateException("Failed to register servlet with name '" + servletName + "'. " +
				"Check if there is another servlet registered under the same name.");
	}
	
	
	registration.setLoadOnStartup(1);
	registration.addMapping(getServletMappings()); //调用者必须实现
	registration.setAsyncSupported(isAsyncSupported()); //默认就是开启了支持异步的

	//处理自定义的Filter进来，一般我们Filter不这么加进来，而是自己@WebFilter，或者借助Spring，  备注：这里添加进来的Filter都仅仅只拦截过滤上面注册的dispatchServlet
	Filter[] filters = getServletFilters();
	if (!ObjectUtils.isEmpty(filters)) {
		for (Filter filter : filters) {
			registerServletFilter(servletContext, filter);
		}
	}
	
	//这个很清楚：调用者若相对dispatcherServlet有自己更个性化的参数设置，复写此方法即可
	customizeRegistration(registration);
}


super如下：
@Override
public void onStartup(ServletContext servletContext) throws ServletException {
	// 创建根上下文
	registerContextLoaderListener(servletContext);
}

protected void registerContextLoaderListener(ServletContext servletContext) {
	WebApplicationContext rootAppContext = createRootApplicationContext();
	if (rootAppContext != null) {
		// 创建listener 并且把已经创建好的容器放进去
		ContextLoaderListener listener = new ContextLoaderListener(rootAppContext);
		//放入监听器需要的一些上下文，此处木有。一般都为null即可~~~。若有需要（自己定制），子类复写此方法即可
		listener.setContextInitializers(getRootApplicationContextInitializers());
		// 把监听器加入进来  这样该监听器就能监听ServletContext了，并且执行contextInitialized方法
		servletContext.addListener(listener);
	}
}

protected WebApplicationContext createRootApplicationContext() {
	Class<?>[] configClasses = getRootConfigClasses();
	if (!ObjectUtils.isEmpty(configClasses)) {
		AnnotationConfigWebApplicationContext context = new AnnotationConfigWebApplicationContext();
		//配置文件可以有多个  会以累加的形式添加进去
		context.register(configClasses);
		return context;
	}
	else {
		return null;
	}
}
```

### tomcat端

org.apache.catalina.startup.ContextConfig#processServletContainerInitializers

```java
List<ServletContainerInitializer> detectedScis;
try {
    WebappServiceLoader<ServletContainerInitializer> loader = new WebappServiceLoader<>(context);
    detectedScis = loader.load(ServletContainerInitializer.class);
} catch (IOException e) {
    log.error(sm.getString(
            "contextConfig.servletContainerInitializerFail",
            context.getName()),
        e);
    ok = false;
    return;
}
```

org.apache.catalina.core.StandardContext#startInternal

```java
            // Call ServletContainerInitializers
            for (Map.Entry<ServletContainerInitializer, Set<Class<?>>> entry :
                initializers.entrySet()) {
                try {
                    entry.getKey().onStartup(entry.getValue(),
                            getServletContext());
                } catch (ServletException e) {
                    log.error(sm.getString("standardContext.sciFail"), e);
                    ok = false;
                    break;
                }
            }
```



## 四大组件

HandlerMapping

下面的图已经过时

![image-20191217144119968](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191217144119968.png)

HandlerAdapter

HandlerException

ResolverViewResolver

## 处理请求

org.springframework.web.servlet.FrameworkServlet

```java
	protected void service(HttpServletRequest request, HttpServletResponse response)
			throws ServletException, IOException {

		HttpMethod httpMethod = HttpMethod.resolve(request.getMethod());
		if (httpMethod == HttpMethod.PATCH || httpMethod == null) {
			processRequest(request, response);
		}
		else {
			super.service(request, response);
		}
	}
```

org.springframework.web.servlet.FrameworkServlet#doGet

org.springframework.web.servlet.FrameworkServlet#processRequest

org.springframework.web.servlet.DispatcherServlet#doService

org.springframework.web.servlet.DispatcherServlet#doDispatch

```java
	protected void doDispatch(HttpServletRequest request, HttpServletResponse response) throws Exception {
		HttpServletRequest processedRequest = request;
		HandlerExecutionChain mappedHandler = null;
		boolean multipartRequestParsed = false;

		WebAsyncManager asyncManager = WebAsyncUtils.getAsyncManager(request);

		try {
			ModelAndView mv = null;
			Exception dispatchException = null;

			try {
				processedRequest = checkMultipart(request);
				multipartRequestParsed = (processedRequest != request);

				// Determine handler for the current request.
        // 获取handler
				mappedHandler = getHandler(processedRequest);
				if (mappedHandler == null) {
					noHandlerFound(processedRequest, response);
					return;
				}

				// Determine handler adapter for the current request.
        // 决定handler适配器，根据handler类型选择handlerAdapter（boolean supports(Object handler)）
				HandlerAdapter ha = getHandlerAdapter(mappedHandler.getHandler());

				// Process last-modified header, if supported by the handler.
				String method = request.getMethod();
				boolean isGet = "GET".equals(method);
				if (isGet || "HEAD".equals(method)) {
					long lastModified = ha.getLastModified(request, mappedHandler.getHandler());
					if (logger.isDebugEnabled()) {
						logger.debug("Last-Modified value for [" + getRequestUri(request) + "] is: " + lastModified);
					}
					if (new ServletWebRequest(request, response).checkNotModified(lastModified) && isGet) {
						return;
					}
				}

				if (!mappedHandler.applyPreHandle(processedRequest, response)) {
					return;
				}

				// Actually invoke the handler.
				mv = ha.handle(processedRequest, response, mappedHandler.getHandler());

				if (asyncManager.isConcurrentHandlingStarted()) {
					return;
				}

				applyDefaultViewName(processedRequest, mv);
				mappedHandler.applyPostHandle(processedRequest, response, mv);
			}
			catch (Exception ex) {
				dispatchException = ex;
			}
			catch (Throwable err) {
				// As of 4.3, we're processing Errors thrown from handler methods as well,
				// making them available for @ExceptionHandler methods and other scenarios.
				dispatchException = new NestedServletException("Handler dispatch failed", err);
			}
			processDispatchResult(processedRequest, response, mappedHandler, mv, dispatchException);
		}
		catch (Exception ex) {
			triggerAfterCompletion(processedRequest, response, mappedHandler, ex);
		}
		catch (Throwable err) {
			triggerAfterCompletion(processedRequest, response, mappedHandler,
					new NestedServletException("Handler processing failed", err));
		}
		finally {
			if (asyncManager.isConcurrentHandlingStarted()) {
				// Instead of postHandle and afterCompletion
				if (mappedHandler != null) {
					mappedHandler.applyAfterConcurrentHandlingStarted(processedRequest, response);
				}
			}
			else {
				// Clean up any resources used by a multipart request.
				if (multipartRequestParsed) {
					cleanupMultipart(processedRequest);
				}
			}
		}
	}
```





![image-20191217141620825](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191217141620825.png)

tomcat启动，如果设置loadOnStartUp为1，则开始初始化servlet，否则要等到第一次请求才初始化servlet，org.apache.catalina.core.StandardWrapper#initServlet

调用dispatcherServlet（org.springframework.web.servlet.HttpServletBean#init->org.springframework.web.servlet.FrameworkServlet#initServletBean）方法，初始化handler和映射

使用spring实现mvc设计模式

![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/springmvc11.png)

![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/springmvc.png)

url进入HandlerMapping，找到具体的controller实现类

![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/springmvc2.png)

![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/springmvc3.png)

核心组件

![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/springmvc4.png)



1:首先方法进入：doDispatch
2:checkMultipart() 判断当前请求是否有文件
3:getHandler（） ：通过HandleMapping去找一个Controller对象 
	3.1:扩展点1：HandleMapping
	3.2: Spring boot 扩展Spring mvc 其中就扩展了 HandleMapping 去解析静态资源
4: getHandlerAdapter（）: 根据你controller的类型去找一个适配器
	4.1:  因为Controller有很多种不同的注册方式 所以需要不同的适配器
	4.2:扩展点2：HandlerAdapter
5:handle() : 执行Controller逻辑并且进行视图裁决（判断是要重定向还是转发还是响应页面）
	5.1invokeForRequest()：执行方法的全部逻辑
	5.2：首先给参数赋值  
		5.2.1:参数赋值的扩展点：HandlerMethodArgumentResolver 
	5.3：调用invoke（）指定方法
6:setResponseStatus（）设置ResponseStatus响应状态码 对标：@ResponseStatus注解
7：handleReturnValue（） 进行视图裁决
	7.1:扩展点:returnValueHandlers 通过这个对象来进行判断接下来视图怎么做、
8：handler.handleReturnValue（） 对冲顶于返回值处理（判断是否需要响应还是需要重定向）
	8.1： 如果是@ResponseBody 注解又有一个扩展点:HttpMessageConverter
9:getModelAndView() 重新封装一个ModelAndView对象 
	9.1：如果不需要渲染视图（如果是重定向 || 响应视图的话） 就会返回null
	9.2: mavContainer.isRequestHandled() 判断是否需要重定向或响应
	9.3: 同时会把model里面的参数放到request.setAttribute（说明model的作用域是request作用域）
10：processDispatchResult（）：开始做视图渲染
	10.1:判断是否需要响应异常视图
	10.2:扩展点：ViewResolver
	10.2：拿到视图名称 封装一个视图对象 进行forward





## reference

http://www.it165.net/pro/html/201502/33644.html

https://blog.csdn.net/and1kaney/article/details/51214193