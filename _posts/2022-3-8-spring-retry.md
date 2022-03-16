---
date: 2022-3-8
layout: default
title: spring-retry



---

# spring-retry

初始化上下文并绑定 -> 回调监听器open判断是否可以重试 -> 回调重试策略start方法 -> 通过重试策略判断是否可以重试 -> 可以的话执行业务代码块 -> 下面两个分支 成功/异常

成功：回调重试策略的close -> 回调监听器的close -> 清除上下文              链路 ①

异常：回调重试策略的registerThrowable -> 回调监听器的onError -> 回调回退策略的backoff -> 如果设置了 Retrystate，判断是否需要抛异常阻断重试 -> 兜底/补偿逻辑 -> 链路 ①



```java
public class RetryTemplate implements RetryOperations {

    protected RetryContext open(RetryPolicy retryPolicy, RetryState state) {
        // 如果是无状态的，每次都调用 org.springframework.retry.RetryPolicy.open创建
        if (state == null) {
            return doOpenInternal(retryPolicy);
        }

        Object key = state.getKey();
        // 如果有状态，但设置了强制刷新，同样 org.springframework.retry.RetryPolicy.open创建，并写入 state.key
        if (state.isForceRefresh()) {
            return doOpenInternal(retryPolicy, state);
        }
        // 尝试从缓存获取，不存在走新建
        if (!this.retryContextCache.containsKey(key)) {
            // The cache is only used if there is a failure.
            return doOpenInternal(retryPolicy, state);
        }
        // 缓存获取
        RetryContext context = this.retryContextCache.get(key);
        if (context == null) {
            // 异常场景
            if (this.retryContextCache.containsKey(key)) {
                throw new RetryException("Inconsistent state for failed item: no history found. "
                        + "Consider whether equals() or hashCode() for the item might be inconsistent, "
                        + "or if you need to supply a better ItemKeyGenerator");
            }
            // 因为整体没有锁，所以有这一步作为补偿（没仔细琢磨，会不会有并发逻辑）
            return doOpenInternal(retryPolicy, state);
        }

        // 因为是缓存，所以同一个 state.key 会共享这个上下文，清除会影响其他正在校验这几个key的地方
        context.removeAttribute(RetryContext.CLOSED);
        context.removeAttribute(RetryContext.EXHAUSTED);
        context.removeAttribute(RetryContext.RECOVERED);
        return context;

    }
}
```



```java
@Configuration
public class RetryConfiguration extends AbstractPointcutAdvisor implements IntroductionAdvisor, BeanFactoryAware {


  @PostConstruct
  public void init() {
    Set<Class> retryableAnnotationTypes = new LinkedHashSet<Class>(1);
    retryableAnnotationTypes.add(Retryable.class);
        // 切点定义，也就是所有被 @Retryable标识的方法
    this.pointcut = buildPointcut(retryableAnnotationTypes);
        // 切面构建
    this.advice = buildAdvice();
    if (this.advice instanceof BeanFactoryAware) {
      ((BeanFactoryAware) this.advice).setBeanFactory(beanFactory);
    }
  }

  protected Advice buildAdvice() {
        // 看这个实现
    AnnotationAwareRetryOperationsInterceptor interceptor = new AnnotationAwareRetryOperationsInterceptor();
    if (retryContextCache != null) {
      interceptor.setRetryContextCache(retryContextCache);
    }
    if (retryListeners != null) {
      interceptor.setListeners(retryListeners);
    }
    if (methodArgumentsKeyGenerator != null) {
      interceptor.setKeyGenerator(methodArgumentsKeyGenerator);
    }
    if (newMethodArgumentsIdentifier != null) {
      interceptor.setNewItemIdentifier(newMethodArgumentsIdentifier);
    }
    if (sleeper != null) {
      interceptor.setSleeper(sleeper);
    }
    return interceptor;
  }
}
```



```java
public class AnnotationAwareRetryOperationsInterceptor implements IntroductionInterceptor, BeanFactoryAware {

  @Override
  public Object invoke(MethodInvocation invocation) throws Throwable {
        // 获取切面代理
    MethodInterceptor delegate = getDelegate(invocation.getThis(), invocation.getMethod());
    if (delegate != null) {
            // 执行代理方法
      return delegate.invoke(invocation);
    }
    else {
      return invocation.proceed();
    }
  }
}
```



```java
public class RetryOperationsInterceptor implements MethodInterceptor {

    private RetryOperations retryOperations = new RetryTemplate();

    public Object invoke(final MethodInvocation invocation) throws Throwable {

        String name;
        if (StringUtils.hasText(label)) {
            name = label;
        } else {
            name = invocation.getMethod().toGenericString();
        }
        final String label = name;
        // 构建 org.springframework.retry.RetryCallback
        RetryCallbackretryCallback = new MethodInvocationRetryCallback(
                invocation, label) {

            @Override
            public Object doWithRetry(RetryContext context) throws Exception {

                context.setAttribute(RetryContext.NAME, label);

                if (invocation instanceof ProxyMethodInvocation) {
                    try {
                        // 回调业务代码块
                        return ((ProxyMethodInvocation) invocation).invocableClone().proceed();
                    } catch (Exception e) {
                        throw e;
                    } catch (Error e) {
                        throw e;
                    } catch (Throwable e) {
                        throw new IllegalStateException(e);
                    }
                } else {
                    throw new IllegalStateException(
                            "MethodInvocation of the wrong type detected - this should not happen with Spring AOP, "
                                    + "so please raise an issue if you see this exception");
                }
            }

        };

        // 根据是否有 @Recover 兜底/补偿方法，调用模板的不同方法
        if (recoverer != null) {
            RetryOperationsInterceptor.ItemRecovererCallback recoveryCallback = new RetryOperationsInterceptor.ItemRecovererCallback(invocation.getArguments(), recoverer);
            return this.retryOperations.execute(retryCallback, recoveryCallback);
        }

        return this.retryOperations.execute(retryCallback);

    }

}
```

```java
public class StatefulRetryOperationsInterceptor implements MethodInterceptor {

    private RetryOperations retryOperations;

    @Override
    public Object invoke(final MethodInvocation invocation) throws Throwable {

        if (this.logger.isDebugEnabled()) {
            this.logger.debug("Executing proxied method in stateful retry: " + invocation.getStaticPart() + "("
                    + ObjectUtils.getIdentityHexString(invocation) + ")");
        }

        Object[] args = invocation.getArguments();
        Object defaultKey = Arrays.asList(args);
        if (args.length == 1) {
            defaultKey = args[0];
        }

        Object key = createKey(invocation, defaultKey);
        RetryState retryState = new DefaultRetryState(key,
                this.newMethodArgumentsIdentifier != null && this.newMethodArgumentsIdentifier.isNew(args),
                this.rollbackClassifier);

        Object result = this.retryOperations.execute(new StatefulRetryOperationsInterceptor.StatefulMethodInvocationRetryCallback(invocation, label),
                this.recoverer != null ? new StatefulRetryOperationsInterceptor.ItemRecovererCallback(args, this.recoverer) : null, retryState);

        if (this.logger.isDebugEnabled()) {
            this.logger.debug("Exiting proxied method in stateful retry with result: (" + result + ")");
        }

        return result;
    }
}
```



## 参考

https://blog.51cto.com/u_15127644/2880409

