---
date: 2020-5-30
layout: default
title: spring-transactional
---

# spring声明式事务

## 传统jdbc事务管理

```java
	private DataSource dataSource = null;
 
  public void setDataSource(DataSource dataSource){
    this.dataSource = dataSource;
  }
  
	public void update() {
    Connection conn = null;
    PreparedStatement pstmt = null;
    try {
      conn = dataSource.getConnection();
      conn.setAutoCommit(false);//设置事务非自动提交
      String sql = "update testTable set name='测试数据' where id = '1'";
      pstmt = conn.prepareStatement(sql);
      pstmt.execute();
      conn.commit();//提交事务
    } catch (Exception e) {
      try {
        conn.rollback();//事务回滚
      } catch (Exception e1) {
        e1.printStackTrace();
      }
      e.printStackTrace();
    } finally {
      try {
        if(pstmt!=null)
          pstmt.close();
        if (conn != null)
          conn.close();
      } catch (SQLException e) {
        e.printStackTrace();
      }
    }
  }
```



Spring事务实现基于AOP实现，而AOP的核心是代理和回调（或者称之为拦截器），对于Spring注解事务，service层的业务类（项目开发过程中事务注解一般在service层使用）的**代理类的生成**其实是在IOC容器初始化过程中，实例化Bean的时候就已经生成代理和织入事务处理回调。

Spring注解事务的实现其实由Spring IOC、AOP和事务三大模块支撑

原理：

对于目标类，若方法上有事务注解，则回生成代理类，并织入事务处理的advisor

Spring总是把JDBC相关的`Connection`和`TransactionStatus`实例绑定到`ThreadLocal`。如果一个事务方法从`ThreadLocal`未取到事务，那么它会打开一个新的JDBC连接，同时开启一个新的事务，否则，它就直接使用从`ThreadLocal`获取的JDBC连接以及`TransactionStatus`。

## 事务抽象

![image-20200606163444921](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200606163444921.png)

![image-20200606165653379](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200606165653379.png)

`AbstractPlatformTransactionManager`抽象类实现了Spring事务的标准流程，其子类`DataSourceTransactionManager`是我们使用较多的JDBC单数据源事务管理器，而`JtaTransactionManager`是JTA（Java Transaction API）规范的实现类，另外两个则分别是JavaEE容器*WebLogic*和*WebSphere*的JTA事务管理器的具体实现。

```java
public interface PlatformTransactionManager extends TransactionManager {

  TransactionStatus getTransaction(@Nullable TransactionDefinition definition)
         throws TransactionException;

  void commit(TransactionStatus status) throws TransactionException;

  void rollback(TransactionStatus status) throws TransactionException;

}
```

## @Transactional

| 属性                   | 含义                                                         |
| ---------------------- | ------------------------------------------------------------ |
| propagation            | 事务传播行为                                                 |
| isolation              | 事务隔离级别                                                 |
| readOnly               | 事务的读写性，boolean型                                      |
| timeout                | 超时时间，int型，以秒为单位                                  |
| rollbackFor            | 一组异常类，遇到时回滚。（rollbackFor={SQLException.class}） |
| rollbackForCalssName   | 一组异常类名，遇到回滚，类型为 string[]                      |
| noRollbackFor          | 一组异常类，遇到不回滚                                       |
| norollbackForCalssName | 一组异常类名，遇到时不回滚                                   |

## 传播类型propagation

1. **PROPAGATION_REQUIRED**

必须有逻辑事务，否则新建一个事务，使用PROPAGATION_REQUIRED指定，表示如果当前存在一个逻辑事务，则加入该逻辑事务，否则将新建一个逻辑事务

2. **PROPAGATION_REQUIRES_NEW**

创建新的逻辑事务，使用PROPAGATION_REQUIRES_NEW指定，表示每次都创建新的逻辑事务（物理事务也是不同的）

3. **PROPAGATION_SUPPORTS**

支持当前事务，使用PROPAGATION_SUPPORTS指定，指如果当前存在逻辑事务，就加入到该逻辑事务，如果当前没有逻辑事务，就以非事务方式执行

4. **PROPAGATION_NOT_SUPPORTED**

即以非事务方式执行，如果当前存在逻辑事务，就把当前事务暂停，以非事务方式执行

5. **PROPAGATION_MANDATORY**

必须有事务，否则抛出异常，使用PROPAGATION_MANDATORY指定，使用当前事务执行，如果当前没有事务，则抛出异常（IllegalTransactionStateException）

6. **PROPAGATION_NEVER**

不支持事务，如果当前存在是事务则抛出异常，使用PROPAGATION_NEVER指定，即以非事务方式执行，如果当前存在事务，则抛出异常（IllegalTransactionStateException）

7. **PROPAGATION_NESTED**

嵌套事务支持，使用PROPAGATION_NESTED指定，如果当前存在事务，则在嵌套事务内执行，如果当前不存在事务，则创建一个新的事务，嵌套事务使用数据库中的保存点来实现，即**嵌套事务回滚不影响外部事务，但外部事务回滚将导致嵌套事务回滚**



org.springframework.transaction.support.AbstractPlatformTransactionManager#handleExistingTransaction

```java
// 已经存在事务的情况下，根据事务传播类型做相应处理
private TransactionStatus handleExistingTransaction(
      TransactionDefinition definition, Object transaction, boolean debugEnabled)
      throws TransactionException {

   if (definition.getPropagationBehavior() == TransactionDefinition.PROPAGATION_NEVER) {
      throw new IllegalTransactionStateException(
            "Existing transaction found for transaction marked with propagation 'never'");
   }

   if (definition.getPropagationBehavior() == TransactionDefinition.PROPAGATION_NOT_SUPPORTED) {
      if (debugEnabled) {
         logger.debug("Suspending current transaction");
      }
      // 暂停当前事务
      Object suspendedResources = suspend(transaction);
      boolean newSynchronization = (getTransactionSynchronization() == SYNCHRONIZATION_ALWAYS);
      return prepareTransactionStatus(
            definition, null, false, newSynchronization, debugEnabled, suspendedResources);
   }

   if (definition.getPropagationBehavior() == TransactionDefinition.PROPAGATION_REQUIRES_NEW) {
      if (debugEnabled) {
         logger.debug("Suspending current transaction, creating new transaction with name [" +
               definition.getName() + "]");
      }
      SuspendedResourcesHolder suspendedResources = suspend(transaction);
      try {
         return startTransaction(definition, transaction, debugEnabled, suspendedResources);
      }
      catch (RuntimeException | Error beginEx) {
         resumeAfterBeginException(transaction, suspendedResources, beginEx);
         throw beginEx;
      }
   }

   if (definition.getPropagationBehavior() == TransactionDefinition.PROPAGATION_NESTED) {
      if (!isNestedTransactionAllowed()) {
         throw new NestedTransactionNotSupportedException(
               "Transaction manager does not allow nested transactions by default - " +
               "specify 'nestedTransactionAllowed' property with value 'true'");
      }
      if (debugEnabled) {
         logger.debug("Creating nested transaction with name [" + definition.getName() + "]");
      }
      if (useSavepointForNestedTransaction()) {
         // Create savepoint within existing Spring-managed transaction,
         // through the SavepointManager API implemented by TransactionStatus.
         // Usually uses JDBC 3.0 savepoints. Never activates Spring synchronization.
         DefaultTransactionStatus status =
               prepareTransactionStatus(definition, transaction, false, false, debugEnabled, null);
         status.createAndHoldSavepoint();
         return status;
      }
      else {
         // Nested transaction through nested begin and commit/rollback calls.
         // Usually only for JTA: Spring synchronization might get activated here
         // in case of a pre-existing JTA transaction.
         return startTransaction(definition, transaction, debugEnabled, null);
      }
   }

   // Assumably PROPAGATION_SUPPORTS or PROPAGATION_REQUIRED.
   if (debugEnabled) {
      logger.debug("Participating in existing transaction");
   }
   if (isValidateExistingTransaction()) {
      if (definition.getIsolationLevel() != TransactionDefinition.ISOLATION_DEFAULT) {
         Integer currentIsolationLevel = TransactionSynchronizationManager.getCurrentTransactionIsolationLevel();
         if (currentIsolationLevel == null || currentIsolationLevel != definition.getIsolationLevel()) {
            Constants isoConstants = DefaultTransactionDefinition.constants;
            throw new IllegalTransactionStateException("Participating transaction with definition [" +
                  definition + "] specifies isolation level which is incompatible with existing transaction: " +
                  (currentIsolationLevel != null ?
                        isoConstants.toCode(currentIsolationLevel, DefaultTransactionDefinition.PREFIX_ISOLATION) :
                        "(unknown)"));
         }
      }
      if (!definition.isReadOnly()) {
         if (TransactionSynchronizationManager.isCurrentTransactionReadOnly()) {
            throw new IllegalTransactionStateException("Participating transaction with definition [" +
                  definition + "] is not marked as read-only but existing transaction is");
         }
      }
   }
   boolean newSynchronization = (getTransactionSynchronization() != SYNCHRONIZATION_NEVER);
   return prepareTransactionStatus(definition, transaction, false, newSynchronization, debugEnabled, null);
}
```

## isolation

ISOLATION_DEFAULT：默认隔离级别，即使用底层数据库默认的隔离级别；

ISOLATION_READ_UNCOMMITTED：未提交读；

ISOLATION_READ_COMMITTED：提交读，一般情况下我们使用这个；

ISOLATION_REPEATABLE_READ：可重复读；

ISOLATION_SERIALIZABLE：序列化。

## **事务超时**

设置事务的超时时间，单位为秒，默认为-1表示使用底层事务的超时时间；

​     使用如setTimeout(100)来设置超时时间，如果事务超时将抛出org.springframework.transaction.TransactionTimedOutException异常并将当前事务标记为应该回滚，即超时后事务被自动回滚；

​     可以使用具体事务管理器实现的defaultTimeout属性设置默认的事务超时时间，如DataSourceTransactionManager. setDefaultTimeout(10)。

## 事务只读

将事务标识为只读，只读事务不修改任何数据；

​     对于JDBC只是简单的将连接设置为只读模式，对于更新将抛出异常；

​     而对于一些其他ORM框架有一些优化作用，如在Hibernate中，Spring事务管理器将执行“session.setFlushMode(FlushMode.MANUAL)”即指定Hibernate会话在只读事务模式下不用尝试检测和同步持久对象的状态的更新。



## spring实现

### spring aop的实现

`AbstractAutoProxyCreator`的初始化回调方法`postProcessAfterInitialization`完成了代理类的生成

![image-20200604153930314](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200604153930314.png)

```java
protected Object wrapIfNecessary(Object bean, String beanName, Object cacheKey) {
   if (StringUtils.hasLength(beanName) && this.targetSourcedBeans.contains(beanName)) {
      return bean;
   }
   if (Boolean.FALSE.equals(this.advisedBeans.get(cacheKey))) {
      return bean;
   }
   if (isInfrastructureClass(bean.getClass()) || shouldSkip(bean.getClass(), beanName)) {
      this.advisedBeans.put(cacheKey, Boolean.FALSE);
      return bean;
   }

   // Create proxy if we have advice.
   Object[] specificInterceptors = getAdvicesAndAdvisorsForBean(bean.getClass(), beanName, null);
   if (specificInterceptors != DO_NOT_PROXY) {
      this.advisedBeans.put(cacheKey, Boolean.TRUE);
      Object proxy = createProxy(
            bean.getClass(), beanName, specificInterceptors, new SingletonTargetSource(bean));
      this.proxyTypes.put(cacheKey, proxy.getClass());
      return proxy;
   }

   this.advisedBeans.put(cacheKey, Boolean.FALSE);
   return bean;
}
```

AbstractAdvisorAutoProxyCreator#getAdvicesAndAdvisorsForBean
AbstractAdvisorAutoProxyCreator#findEligibleAdvisors

`findEligibleAdvisors`方法是查找合法的advisor，包含三个主要方法：

- `findCandidateAdvisors`：查找候选的advisor，从源码可看出就是根据`Advisor.class`类型在IOC容器中查找
- `findAdvisorsThatCanApply`：遍历候选advisor，判断是否是合法的advisor，此处重点关注事务advisor的判断处理
- `sortAdvisors`：给advisor排序



从`AbstractAdvisorAutoProxyCreator`的类图可看出，有4个具体的实现类：

- AnnotationAwareAspectJAutoProxyCreator
- AspectJAwareAdvisorAutoProxyCreator
- DefaultAdvisorAutoProxyCreator
- InfrastructureAdvisorAutoProxyCreator

Spring注解事务使用的是InfrastructureAdvisorAutoProxyCreator

### 入口

当容器开始启动运行的时候就会找到@EnableTransactionManagement注解

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Import(TransactionManagementConfigurationSelector.class)
public @interface EnableTransactionManagement {

	/**
	 * Indicate whether subclass-based (CGLIB) proxies are to be created ({@code true}) as
	 * opposed to standard Java interface-based proxies ({@code false}). The default is
	 * {@code false}. <strong>Applicable only if {@link #mode()} is set to
	 * {@link AdviceMode#PROXY}</strong>.
	 * <p>Note that setting this attribute to {@code true} will affect <em>all</em>
	 * Spring-managed beans requiring proxying, not just those marked with
	 * {@code @Transactional}. For example, other beans marked with Spring's
	 * {@code @Async} annotation will be upgraded to subclass proxying at the same
	 * time. This approach has no negative impact in practice unless one is explicitly
	 * expecting one type of proxy vs another, e.g. in tests.
	 */
	boolean proxyTargetClass() default false;

	/**
	 * Indicate how transactional advice should be applied.
	 * <p><b>The default is {@link AdviceMode#PROXY}.</b>
	 * Please note that proxy mode allows for interception of calls through the proxy
	 * only. Local calls within the same class cannot get intercepted that way; an
	 * {@link Transactional} annotation on such a method within a local call will be
	 * ignored since Spring's interceptor does not even kick in for such a runtime
	 * scenario. For a more advanced mode of interception, consider switching this to
	 * {@link AdviceMode#ASPECTJ}.
	 */
	AdviceMode mode() default AdviceMode.PROXY;

	/**
	 * Indicate the ordering of the execution of the transaction advisor
	 * when multiple advices are applied at a specific joinpoint.
	 * <p>The default is {@link Ordered#LOWEST_PRECEDENCE}.
	 */
	int order() default Ordered.LOWEST_PRECEDENCE;

}
```



进入注解，发现它使用@Import(TransactionManagementConfigurationSelector.class)

跟进TransactionManagementConfigurationSelector，发现它最终实现的是ImportSelector接口，这个接口可以向IOC容器中以Bean的全类名的方式注入Bean。

AdviceMode在注解@EnableTransactionManagement默认就是PROXY，可见它向容器中注入了两个类，分别是AutoProxyRegistrar和ProxyTransactionManagementConfiguration

```java
public class TransactionManagementConfigurationSelector extends AdviceModeImportSelector<EnableTransactionManagement> {

	/**
	 * Returns {@link ProxyTransactionManagementConfiguration} or
	 * {@code AspectJ(Jta)TransactionManagementConfiguration} for {@code PROXY}
	 * and {@code ASPECTJ} values of {@link EnableTransactionManagement#mode()},
	 * respectively.
	 */
	@Override
	protected String[] selectImports(AdviceMode adviceMode) {
		switch (adviceMode) {
			case PROXY:
				return new String[] {AutoProxyRegistrar.class.getName(),
						ProxyTransactionManagementConfiguration.class.getName()};
			case ASPECTJ:
				return new String[] {determineTransactionAspectClass()};
			default:
				return null;
		}
	}
```

关键2个组件：AutoProxyRegistrar ProxyTransactionManagementConfiguration

### AutoProxyRegistrar

```java
public class AutoProxyRegistrar implements ImportBeanDefinitionRegistrar {

   private final Log logger = LogFactory.getLog(getClass());

   @Override
   public void registerBeanDefinitions(AnnotationMetadata importingClassMetadata, BeanDefinitionRegistry registry) {
      boolean candidateFound = false;
      Set<String> annTypes = importingClassMetadata.getAnnotationTypes();
      for (String annType : annTypes) {
         AnnotationAttributes candidate = AnnotationConfigUtils.attributesFor(importingClassMetadata, annType);
         if (candidate == null) {
            continue;
         }
         Object mode = candidate.get("mode");
         Object proxyTargetClass = candidate.get("proxyTargetClass");
         if (mode != null && proxyTargetClass != null && AdviceMode.class == mode.getClass() &&
               Boolean.class == proxyTargetClass.getClass()) {
            candidateFound = true;
            if (mode == AdviceMode.PROXY) {
               // 前面的代码主要是获取注解类型，注解信息等等。
               // 主要是这个地方，如果必要的话，就向容器中注册一个自动代理创建器。
               AopConfigUtils.registerAutoProxyCreatorIfNecessary(registry);
               if ((Boolean) proxyTargetClass) {
                  AopConfigUtils.forceAutoProxyCreatorToUseClassProxying(registry);
                  return;
               }
            }
         }
      }
      if (!candidateFound && logger.isInfoEnabled()) {
         String name = getClass().getSimpleName();
         logger.info(String.format("%s was imported but no annotations were found " +
               "having both 'mode' and 'proxyTargetClass' attributes of type " +
               "AdviceMode and boolean respectively. This means that auto proxy " +
               "creator registration and configuration may not have occurred as " +
               "intended, and components may not be proxied as expected. Check to " +
               "ensure that %s has been @Import'ed on the same class where these " +
               "annotations are declared; otherwise remove the import of %s " +
               "altogether.", name, name, name));
      }
   }

}
```



org.springframework.aop.config.AopConfigUtils#registerAutoProxyCreatorIfNecessary(org.springframework.beans.factory.support.BeanDefinitionRegistry)

org.springframework.aop.config.AopConfigUtils#registerAutoProxyCreatorIfNecessary(org.springframework.beans.factory.support.BeanDefinitionRegistry, java.lang.Object)

org.springframework.aop.config.AopConfigUtils#registerOrEscalateApcAsRequired

```java
@Nullable
private static BeanDefinition registerOrEscalateApcAsRequired(Class<?> cls, BeanDefinitionRegistry registry,
        @Nullable Object source) {
    // -- 断言
    Assert.notNull(registry, "BeanDefinitionRegistry must not be null");
    // 先判断有没有org.springframework.aop.config.internalAutoProxyCreator
    // 首次进来，肯定没有
    if (registry.containsBeanDefinition(AUTO_PROXY_CREATOR_BEAN_NAME)) {
        BeanDefinition apcDefinition = registry.getBeanDefinition(AUTO_PROXY_CREATOR_BEAN_NAME);
        if (!cls.getName().equals(apcDefinition.getBeanClassName())) {
            int currentPriority = findPriorityForClass(apcDefinition.getBeanClassName());
            int requiredPriority = findPriorityForClass(cls);
            if (currentPriority < requiredPriority) {
                apcDefinition.setBeanClassName(cls.getName());
            }
        }
        return null;
    }
    // -- 将cls也就是InfrastructureAdvisorAutoProxyCreator包装成RootBeanDefinition
    RootBeanDefinition beanDefinition = new RootBeanDefinition(cls);
    beanDefinition.setSource(source);
    beanDefinition.getPropertyValues().add("order", Ordered.HIGHEST_PRECEDENCE);
    beanDefinition.setRole(BeanDefinition.ROLE_INFRASTRUCTURE);
    // -- 将beanDefinition注册到IOC容器中，Bean的
    // -- 名字就叫org.springframework.aop.config.internalAutoProxyCreator
    registry.registerBeanDefinition(AUTO_PROXY_CREATOR_BEAN_NAME, beanDefinition);
    return beanDefinition;
}
```

1. AutoProxyRegistrar作用将InfrastructureAdvisorAutoProxyCreator包装成RootBeanDefinition，该类主要是SmartInstantiationAwareBeanPostProcessor，**一个bean后置处理器**，作用是利用后置处理器机制在对象创建以后，对对象进行包装，返回一个代理对象(增强器)，代理对象执行方法，利用拦截器链进行调用

```
InfrastructureAdvisorAutoProxyCreator
    --AbstractAdvisorAutoProxyCreator
        --AbstractAdvisorAutoProxyCreator
            --ProxyProcessorSupport
            --SmartInstantiationAwareBeanPostProcessor  // 跟AOP是原理是一样的
                --InstantiationAwareBeanPostProcessor
                    --BeanPostProcessor
            --BeanFactoryAware
```

![image-20200606171354156](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200606171354156.png)

```java
/**
 * Create a proxy with the configured interceptors if the bean is
 * identified as one to proxy by the subclass.
 * @see #getAdvicesAndAdvisorsForBean
 */
@Override
public Object postProcessAfterInitialization(@Nullable Object bean, String beanName) throws BeansException {
    if (bean != null) {
        Object cacheKey = getCacheKey(bean.getClass(), beanName);
        if (!this.earlyProxyReferences.contains(cacheKey)) {
            return wrapIfNecessary(bean, beanName, cacheKey);
        }
    }
    return bean;
}
```

### ProxyTransactionManagementConfiguration

2. ProxyTransactionManagementConfiguration，注入一个BeanFactoryTransactionAttributeSourceAdvisor bean

```java
@Configuration(proxyBeanMethods = false)
@Role(BeanDefinition.ROLE_INFRASTRUCTURE)
public class ProxyTransactionManagementConfiguration extends AbstractTransactionManagementConfiguration {

	@Bean(name = TransactionManagementConfigUtils.TRANSACTION_ADVISOR_BEAN_NAME)
	@Role(BeanDefinition.ROLE_INFRASTRUCTURE)
	public BeanFactoryTransactionAttributeSourceAdvisor transactionAdvisor(
			TransactionAttributeSource transactionAttributeSource, TransactionInterceptor transactionInterceptor) {
	
		BeanFactoryTransactionAttributeSourceAdvisor advisor = new BeanFactoryTransactionAttributeSourceAdvisor();
    // 向切面中注入注解解析器,专门来解析事务注解的
		advisor.setTransactionAttributeSource(transactionAttributeSource);
    // 向切面中注入事务的拦截器,专门来拦截方法,包括事务的提交以及回滚操作
		advisor.setAdvice(transactionInterceptor);
		if (this.enableTx != null) {
			advisor.setOrder(this.enableTx.<Integer>getNumber("order"));
		}
		return advisor;
	}

	@Bean
	@Role(BeanDefinition.ROLE_INFRASTRUCTURE)
	public TransactionAttributeSource transactionAttributeSource() {
    // transactional注解属性
		return new AnnotationTransactionAttributeSource();
	}

	@Bean
	@Role(BeanDefinition.ROLE_INFRASTRUCTURE)
	public TransactionInterceptor transactionInterceptor(TransactionAttributeSource transactionAttributeSource) {
		// 事务拦截器
    TransactionInterceptor interceptor = new TransactionInterceptor();
		interceptor.setTransactionAttributeSource(transactionAttributeSource);
		if (this.txManager != null) {
			interceptor.setTransactionManager(this.txManager);
		}
		return interceptor;
	}

}
```

#### TransactionInterceptor

![image-20200606172804799](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200606172804799.png)

org.springframework.transaction.interceptor.TransactionInterceptor#invoke

```java
public Object invoke(MethodInvocation invocation) throws Throwable {
   // Work out the target class: may be {@code null}.
   // The TransactionAttributeSource should be passed the target class
   // as well as the method, which may be from an interface.
   Class<?> targetClass = (invocation.getThis() != null ? AopUtils.getTargetClass(invocation.getThis()) : null);

   // Adapt to TransactionAspectSupport's invokeWithinTransaction...
   return invokeWithinTransaction(invocation.getMethod(), targetClass, invocation::proceed);
}
```

org.springframework.transaction.interceptor.TransactionAspectSupport#invokeWithinTransaction

```java
@Nullable
protected Object invokeWithinTransaction(Method method, @Nullable Class<?> targetClass,
        final InvocationCallback invocation) throws Throwable {
    // If the transaction attribute is null, the method is non-transactional.
    TransactionAttributeSource tas = getTransactionAttributeSource();
        // -- 拿到事务注解信息包括事务的qualifier和rollback信息
    final TransactionAttribute txAttr = (tas != null ? tas.getTransactionAttribute(method, targetClass) : null);
        // -- 获取事务管理器
    final PlatformTransactionManager tm = determineTransactionManager(txAttr);
        // -- 事务连接点的定义信息
    final String joinpointIdentification = methodIdentification(method, targetClass, txAttr);
    if (txAttr == null || !(tm instanceof CallbackPreferringPlatformTransactionManager)) {
        // 创建并开启事务
        TransactionInfo txInfo = createTransactionIfNecessary(tm, txAttr, joinpointIdentification);
        Object retVal = null;
        try {
            // This is an around advice: Invoke the next interceptor in the chain.
            // This will normally result in a target object being invoked.
                        // -- 调用目标方法
            retVal = invocation.proceedWithInvocation();
        }
        catch (Throwable ex) {
            // target invocation exception
                        // -- 出现异常了,获取事务管理器,进行事务的回滚
            completeTransactionAfterThrowing(txInfo, ex);
            throw ex;
        }
        finally {
            // 清理当前线程事务信息
            cleanupTransactionInfo(txInfo);
        }
                // -- 未出现异常,也获取事务管理器则进行事务的提交
        commitTransactionAfterReturning(txInfo);
        return retVal;
    }
    .........
```

org.springframework.transaction.interceptor.TransactionAspectSupport#createTransactionIfNecessary

org.springframework.transaction.support.AbstractPlatformTransactionManager#getTransaction

​	org.springframework.jdbc.datasource.DataSourceTransactionManager#doGetTransaction

​	org.springframework.transaction.support.AbstractPlatformTransactionManager#startTransaction

​		org.springframework.jdbc.datasource.DataSourceTransactionManager#doBegin

```java
if (con.getAutoCommit()) {
				txObject.setMustRestoreAutoCommit(true);
				if (logger.isDebugEnabled()) {
					logger.debug("Switching JDBC Connection [" + con + "] to manual commit");
				}
  			// jdbc规范，开启手动事务是con.setAutoCommit(false)，JDBC事务默认是开启的，并且是自动提交：
				con.setAutoCommit(false);
			}

			// Bind the connection holder to the thread.将connection绑定到当前线程本地变量resources
			if (txObject.isNewConnectionHolder()) {
				TransactionSynchronizationManager.bindResource(obtainDataSource(), txObject.getConnectionHolder());
			}
```

总结：

1. 通过注解@EnableTransactionManagement中的@Import(TransactionManagementConfigurationSelector.class)给容器中导入了两个组件，分别是：AutoProxyRegistrar和ProxyTransactionManagementConfiguration
2. AutoProxyRegistrar：它是一个后置处理器，给容器中注册一个InfrastructureAdvisorAutoProxyCreator，InfrastructureAdvisorAutoProxyCreator利用后置处理器机制在对象创建以后，对对象进行包装，返回一个代理对象(增强器)，代理对象执行方法，利用拦截器链进行调用。
3. ProxyTransactionManagementConfiguration：给容器中注册事务增强器

- 事务增强器要用事务注解信息：AnnotationTransactionAttributeSource来解析事务注解
- 事务拦截器中：transactionInterceptor()，它是一个TransactionInterceptor(保存了事务属性信息和事务管理器)，而TransactionInterceptor是一个MethodInterceptor，在目标方法执行的时候，执行拦截器链，事务拦截器(首先获取事务相关的属性，再获取PlatformTransactionManager，如果没有指定任何transactionManager，最终会从容器中按照类型获取一个PlatformTransactionManager，最后执行目标方法，如果异常，便获取到事务管理器进行回滚，如果正常，同样拿到事务管理器提交事务。

### 问题

BeanFactoryTransactionAttributeSourceAdvisor怎么插入到aop里？

`AbstractAutoProxyCreator`后置处理器会从容器里找`Advisor.class`类型的bean

org.springframework.aop.framework.autoproxy.AbstractAdvisorAutoProxyCreator#getAdvicesAndAdvisorsForBean



```java
public class BeanFactoryTransactionAttributeSourceAdvisor extends AbstractBeanFactoryPointcutAdvisor {

	@Nullable
	private TransactionAttributeSource transactionAttributeSource;
	// 定义切点，根据TransactionAttributeSource选择要代理的bean
	private final TransactionAttributeSourcePointcut pointcut = new TransactionAttributeSourcePointcut() {
		@Override
		@Nullable
		protected TransactionAttributeSource getTransactionAttributeSource() {
			return transactionAttributeSource;
		}
	};


	/**
	 * Set the transaction attribute source which is used to find transaction
	 * attributes. This should usually be identical to the source reference
	 * set on the transaction interceptor itself.
	 * @see TransactionInterceptor#setTransactionAttributeSource
	 */
	public void setTransactionAttributeSource(TransactionAttributeSource transactionAttributeSource) {
		this.transactionAttributeSource = transactionAttributeSource;
	}

	/**
	 * Set the {@link ClassFilter} to use for this pointcut.
	 * Default is {@link ClassFilter#TRUE}.
	 */
	public void setClassFilter(ClassFilter classFilter) {
		this.pointcut.setClassFilter(classFilter);
	}

	@Override
	public Pointcut getPointcut() {
		return this.pointcut;
	}

}
```

org.springframework.transaction.interceptor.TransactionAttributeSourcePointcut#matches

```java
public boolean matches(Method method, Class<?> targetClass) {
	if (TransactionalProxy.class.isAssignableFrom(targetClass)) {
		return false;
	}
	//获取TransactionAttributeSource
	TransactionAttributeSource tas = getTransactionAttributeSource();
	//从方法上获取到事务属性（即使用Transactional注解配置的信息），则匹配成功
	return (tas == null || tas.getTransactionAttribute(method, targetClass) != null);
}


```

org.springframework.transaction.annotation.AnnotationTransactionAttributeSource

```java
protected TransactionAttribute determineTransactionAttribute(AnnotatedElement ae) {
	if (ae.getAnnotations().length > 0) {
		for (TransactionAnnotationParser annotationParser : this.annotationParsers) {
			//解析方法上的事务属性
			TransactionAttribute attr = annotationParser.parseTransactionAnnotation(ae);
			if (attr != null) {
				return attr;
			}
		}
	}
	return null;
}
```

### spring事务同步

#### 事务同步

事务处理前，处理后的一些回调

```java
// @since 02.06.2003  实现了java.io.Flushable接口
public interface TransactionSynchronization extends Flushable {

	int STATUS_COMMITTED = 0;
	int STATUS_ROLLED_BACK = 1;
	int STATUS_UNKNOWN = 2;

	// 事务赞提suspend的时候调用此方法
	// 实现这个方法的目的一般是释放掉绑定的resources 
	// TransactionSynchronizationManager#unbindResource
	default void suspend() {
	}
	// 事务恢复时候调用
	// TransactionSynchronizationManager#bindResource
	default void resume() {
	}

	// 将基础会话刷新到数据存储区（如果适用） 比如Hibernate/Jpa的session
	@Override
	default void flush() {
	}

	// 在事务提交之前促发。在AbstractPlatformTransactionManager.processCommit方法里 commit之前触发
	// 事务提交之前，比如flushing SQL statements to the database
	// 请注意：若此处发生了异常，会导致回滚~
	default void beforeCommit(boolean readOnly) {
	}
	// 在beforeCommit之后，在commit/rollback之前执行
	// 它和beforeCommit还有个非常大的区别是：即使beforeCommit抛出异常了  这个也会执行
	default void beforeCompletion() {
	}

	// 这个就非常重要了，它是事务提交（注意事务已经成功提交，数据库已经持久化完成这条数据了）后执行  注意此处是成功提交而没有异常
	// javadoc说了：此处一般可以发短信或者email等操作~~因为事务已经成功提交了
	
	// =====但是但是但是：======
	// 事务虽然已经提交，但事务资源（链接connection）可能仍然是活动的和可访问的。
	// 因此，此时触发的任何数据访问代码仍将“参与”原始事务 允许执行一些清理（不再执行提交操作！）
	// 除非它明确声明它需要在单独的事务中运行。
	default void afterCommit() {
	}

	// 和上面的区别在于：即使抛出异常回滚了  它也会执行的。它的notice同上
	default void afterCompletion(int status) {
	}
}
```

#### 事务同步管理器

通过threadLocal实现不同线程拥有不同的连接资源

```java
// @since 02.06.2003  它是个抽象类，但是没有任何子类  因为它所有的方法都是静态的
public abstract class TransactionSynchronizationManager {

	// ======保存着一大堆的ThreadLocal 这里就是它的核心存储======

	//  应用代码随事务的声明周期绑定的对象  比如：DataSourceTransactionManager有这么做：
	//TransactionSynchronizationManager.bindResource(obtainDataSource(), txObject.getConnectionHolder());
	// TransactionSynchronizationManager.bindResource(obtainDataSource(), suspendedResources);
	// 简单理解为当前线程的数据存储中心~~~~
	private static final ThreadLocal<Map<Object, Object>> resources = new NamedThreadLocal<>("Transactional resources");

	// 使用的同步器，用于应用扩展
	// TransactionSynchronization同步器是最为重要的一个扩展点~~~ 这里是个set 所以每个线程都可以注册N多个同步器
	private static final ThreadLocal<Set<TransactionSynchronization>> synchronizations = new NamedThreadLocal<>("Transaction synchronizations");
	
	// 事务的名称  
	private static final ThreadLocal<String> currentTransactionName = new NamedThreadLocal<>("Current transaction name");
	// 事务是否是只读  
	private static final ThreadLocal<Boolean> currentTransactionReadOnly = new NamedThreadLocal<>("Current transaction read-only status");
	// 事务的隔离级别
	private static final ThreadLocal<Integer> currentTransactionIsolationLevel = new NamedThreadLocal<>("Current transaction isolation level");
	// 事务是否开启   actual：真实的
	private static final ThreadLocal<Boolean> actualTransactionActive = new NamedThreadLocal<>("Actual transaction active");

	// 返回的是个只读视图
	public static Map<Object, Object> getResourceMap() {
		Map<Object, Object> map = resources.get();
		return (map != null ? Collections.unmodifiableMap(map) : Collections.emptyMap());
	}

	public static boolean hasResource(Object key) { ... }
	public static Object getResource(Object key) { ... }
	
	// actualKey：确定的key  拆包后的
	@Nullable
	private static Object doGetResource(Object actualKey) {
		Map<Object, Object> map = resources.get();
		if (map == null) {
			return null;
		}
		Object value = map.get(actualKey);
		// Transparently remove ResourceHolder that was marked as void...
		// 如果ResourceHolder 被标记为了void空白了。此处直接从map里移除掉对应的key 
		// ~~~~~~~并且返回null~~~~~~~~~~~
		if (value instanceof ResourceHolder && ((ResourceHolder) value).isVoid()) {
			map.remove(actualKey);
			// Remove entire ThreadLocal if empty...
			if (map.isEmpty()) {
				resources.remove();
			}
			value = null;
		}
		return value;
	}

	// 逻辑很简单，就是和当前线程绑定一个Map，并且处理ResourceHolder 如果isVoid就抛错
	public static void bindResource(Object key, Object value) throws IllegalStateException {
		Object actualKey = TransactionSynchronizationUtils.unwrapResourceIfNecessary(key);
		Assert.notNull(value, "Value must not be null");
		Map<Object, Object> map = resources.get();
		// set ThreadLocal Map if none found
		if (map == null) {
			map = new HashMap<>();
			resources.set(map);
		}
		Object oldValue = map.put(actualKey, value);
		// Transparently suppress a ResourceHolder that was marked as void...
		if (oldValue instanceof ResourceHolder && ((ResourceHolder) oldValue).isVoid()) {
			oldValue = null;
		}
		if (oldValue != null) {
			throw new IllegalStateException("Already value [" + oldValue + "] for key [" +
					actualKey + "] bound to thread [" + Thread.currentThread().getName() + "]");
		}
	}

	public static Object unbindResource(Object key) throws IllegalStateException { ... }
	public static Object unbindResourceIfPossible(Object key) { ... }
	

	// 同步器是否是激活状态~~~  若是激活状态就可以执行同步器里的相关回调方法了
	public static boolean isSynchronizationActive() {
		return (synchronizations.get() != null);
	}

	// 如果事务已经开启了，就不能再初始化同步器了  而是直接注册
	public static void initSynchronization() throws IllegalStateException {
		if (isSynchronizationActive()) {
			throw new IllegalStateException("Cannot activate transaction synchronization - already active");
		}
		logger.trace("Initializing transaction synchronization");
		synchronizations.set(new LinkedHashSet<>());
	}

	// 注册同步器TransactionSynchronization   这个非常重要 下面有详细介绍这个接口
	// 注册的时候要求当前线程的事务已经是激活状态的  而不是随便就可以调用的哦~~~
	public static void registerSynchronization(TransactionSynchronization synchronization) throws IllegalStateException {
		Assert.notNull(synchronization, "TransactionSynchronization must not be null");
		if (!isSynchronizationActive()) {
			throw new IllegalStateException("Transaction synchronization is not active");
		}
		synchronizations.get().add(synchronization);
	}


	// 返回的是只读视图  并且，并且支持AnnotationAwareOrderComparator.sort(sortedSynchs); 这样排序~~
	public static List<TransactionSynchronization> getSynchronizations() throws IllegalStateException { ... }
	public static void clearSynchronization() throws IllegalStateException { ... }

	... // 省略name等其余几个属性的get/set方法  因为没有任何逻辑
	// 这个方法列出来，应该下面会解释
	public static void setActualTransactionActive(boolean active) {
		actualTransactionActive.set(active ? Boolean.TRUE : null);
	}
	
	// 清楚所有和当前线程相关的（注意：此处只是clear清除，和当前线程的绑定而已~~~）
	public static void clear() {
		synchronizations.remove();
		currentTransactionName.remove();
		currentTransactionReadOnly.remove();
		currentTransactionIsolationLevel.remove();
		actualTransactionActive.remove();
	}
}
```

#### 事务管理

```java
public interface PlatformTransactionManager extends TransactionManager {

  TransactionStatus getTransaction(@Nullable TransactionDefinition definition)
         throws TransactionException;

  void commit(TransactionStatus status) throws TransactionException;

  void rollback(TransactionStatus status) throws TransactionException;

}
```

#### 事务管理抽象

```java
public abstract class AbstractPlatformTransactionManager implements PlatformTransactionManager, Serializable {
	...
	private void processCommit(DefaultTransactionStatus status) throws TransactionException {
		...
		try {
			prepareForCommit(status);
			triggerBeforeCommit(status);
			triggerBeforeCompletion(status);
			...
			doCommit(status);
			
			// 事务正常提交后  当然triggerAfterCompletion方法上面回滚里有而有个执行 此处不贴出了
			try {
				triggerAfterCommit(status);
			} finally {
				triggerAfterCompletion(status, TransactionSynchronization.STATUS_COMMITTED);
			}
		} finally {
			cleanupAfterCompletion(status);
		}
	}
  
  protected final void triggerBeforeCommit(DefaultTransactionStatus status) {
		if (status.isNewSynchronization()) {
			if (status.isDebug()) {
				logger.trace("Triggering beforeCommit synchronization");
			}
      // 事务同步
			TransactionSynchronizationUtils.triggerBeforeCommit(status.isReadOnly());
		}
	}
  
	...
	// 清楚、回收事务相关的资源~~~  并且恢复底层事务（若需要~）
	private void cleanupAfterCompletion(DefaultTransactionStatus status) {
		status.setCompleted();
		if (status.isNewSynchronization()) {
			TransactionSynchronizationManager.clear();
		}
		if (status.isNewTransaction()) {
			doCleanupAfterCompletion(status.getTransaction());
		}
		if (status.getSuspendedResources() != null) {
			if (status.isDebug()) {
				logger.debug("Resuming suspended transaction after completion of inner transaction");
			}
			Object transaction = (status.hasTransaction() ? status.getTransaction() : null);
			resume(transaction, (SuspendedResourcesHolder) status.getSuspendedResources());
		}
	}
}
```

org.springframework.transaction.support.TransactionSynchronizationUtils#triggerBeforeCommit

```java
public static void triggerBeforeCommit(boolean readOnly) {
   // 从事务同步管理中获取所有事务同步
   for (TransactionSynchronization synchronization : TransactionSynchronizationManager.getSynchronizations()) {
     // 依次执行事务同步
      synchronization.beforeCommit(readOnly);
   }
}
```

## Springboot实现

### 1.自动配置的事务管理器

```java
# Auto Configure
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
org.springframework.boot.autoconfigure.jdbc.DataSourceTransactionManagerAutoConfiguration,\
org.springframework.boot.autoconfigure.transaction.TransactionAutoConfiguration,\
```

```java
@Configuration(proxyBeanMethods = false)
@ConditionalOnClass({ JdbcTemplate.class, PlatformTransactionManager.class })
@AutoConfigureOrder(Ordered.LOWEST_PRECEDENCE)
@EnableConfigurationProperties(DataSourceProperties.class)
public class DataSourceTransactionManagerAutoConfiguration {

	@Configuration(proxyBeanMethods = false)
	@ConditionalOnSingleCandidate(DataSource.class)
	static class DataSourceTransactionManagerConfiguration {

		@Bean
		@ConditionalOnMissingBean(PlatformTransactionManager.class)
		DataSourceTransactionManager transactionManager(DataSource dataSource,
				ObjectProvider<TransactionManagerCustomizers> transactionManagerCustomizers) {
			DataSourceTransactionManager transactionManager = new DataSourceTransactionManager(dataSource);
			transactionManagerCustomizers.ifAvailable((customizers) -> customizers.customize(transactionManager));
			return transactionManager;
		}

	}

}
```

### 2.自动开启注解事务的支持



## jdbcTemplate获取connection

```java
public class JdbcTemplate extends JdbcAccessor implements JdbcOperations {
	...
	public <T> T execute(StatementCallback<T> action) throws DataAccessException {
		...
		// dataSource就是此JdbcTemplate所关联的数据源，这个在config配置文件里早就配置好了
		// 显然，这里获取的连接就是事务相关的，和当前想成绑定的connection
		Connection con = DataSourceUtils.getConnection(obtainDataSource());
		...
		finally {
			JdbcUtils.closeStatement(stmt);
			DataSourceUtils.releaseConnection(con, getDataSource());
		}
	}
	...
}
```

org.springframework.jdbc.datasource.DataSourceUtils#getConnection

```java
public static Connection getConnection(DataSource dataSource) throws CannotGetJdbcConnectionException {
   try {
      return doGetConnection(dataSource);
   }
   catch (SQLException ex) {
      throw new CannotGetJdbcConnectionException("Failed to obtain JDBC Connection", ex);
   }
   catch (IllegalStateException ex) {
      throw new CannotGetJdbcConnectionException("Failed to obtain JDBC Connection: " + ex.getMessage());
   }
}

	public static Connection doGetConnection(DataSource dataSource) throws SQLException {
		Assert.notNull(dataSource, "No DataSource specified");

    // 通过同步器拿到connection资源
		ConnectionHolder conHolder = (ConnectionHolder) TransactionSynchronizationManager.getResource(dataSource);
		if (conHolder != null && (conHolder.hasConnection() || conHolder.isSynchronizedWithTransaction())) {
			conHolder.requested();
			if (!conHolder.hasConnection()) {
				logger.debug("Fetching resumed JDBC Connection from DataSource");
				conHolder.setConnection(fetchConnection(dataSource));
			}
			return conHolder.getConnection();
		}
		// Else we either got no holder or an empty thread-bound holder here.

		logger.debug("Fetching JDBC Connection from DataSource");
		Connection con = fetchConnection(dataSource);

		if (TransactionSynchronizationManager.isSynchronizationActive()) {
			try {
				// Use same Connection for further JDBC actions within the transaction.
				// Thread-bound object will get removed by synchronization at transaction completion.
				ConnectionHolder holderToUse = conHolder;
				if (holderToUse == null) {
					holderToUse = new ConnectionHolder(con);
				}
				else {
					holderToUse.setConnection(con);
				}
				holderToUse.requested();
				TransactionSynchronizationManager.registerSynchronization(
						new ConnectionSynchronization(holderToUse, dataSource));
				holderToUse.setSynchronizedWithTransaction(true);
				if (holderToUse != conHolder) {
					TransactionSynchronizationManager.bindResource(dataSource, holderToUse);
				}
			}
			catch (RuntimeException ex) {
				// Unexpected exception from external delegation call -> close Connection and rethrow.
				releaseConnection(con, dataSource);
				throw ex;
			}
		}

		return con;
	}


```

1. 不同类之间的方法调用，如类A的方法a()调用类B的方法b()，这种情况事务是正常起作用的。只要方法a()或b()配置了事务，运行中就会开启事务，产生代理。

若两个方法都配置了事务，两个事务具体以何种方式传播，取决于设置的事务传播特性。

2. 同一个类内方法调用：重点来了，同一个类内的方法调用就没那么简单了，假定类A的方法a()调用方法b()

同一类内方法调用，无论被调用的b()方法是否配置了事务，此事务在被调用时都将不生效。




## 参考

https://segmentfault.com/a/1190000018001752

https://liuxi.name/blog/20171111/spring-transaction-proxy.html

https://zhuanlan.zhihu.com/p/54067384