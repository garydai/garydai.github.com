---
date: 2019-8-18
layout: default

title: spring cloud

---

## spring cloud
### eureka
服务注册

ap集群
### ribbon
客户端负载均衡
![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/ribbon.png)

原理就是：将spring的restTemplate对象添加拦截器，restTemplate.setInterceptors()

loadBalancerInterceptor

实现：

1. 通过eureka客户端获取服务信息
2. 定时刷新服务信息
3. ping 服务是否存活

### feign

类似mabtis的dao，代理http请求
### hystrix 熔断器
方法降级、超时监听、服务熔断、服务限流
### zuul 网关
路由、过滤、容错与回退、集群、高可用
### config 分布式配置
### sleuth 分布式链路跟踪 + zipkin 可视化

![](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/springcloud.png)


