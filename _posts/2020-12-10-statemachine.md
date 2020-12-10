---
date: 2020-12-10
layout: default
title: 状态机引擎


---

# state machine

https://github.com/alibaba/COLA/blob/master/cola-components/cola-component-statemachine

## 模型

1. State：状态
2. Event：事件，状态由事件触发，引起变化
3. Transition：流转，表示从一个状态到另一个状态
4. External Transition：外部流转，两个不同状态之间的流转
5. Internal Transition：内部流转，同一个状态之间的流转
6. Condition：条件，表示是否允许到达某个状态
7. Action：动作，到达某个状态之后，可以做什么
8. StateMachine：状态机

![image-20201210094754635](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20201210094754635.png)

![image-20201210094823800](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20201210094823800.png)

## 使用

```java
private StateMachine<States, Events, Context> buildStateMachine(String machineId) {
        StateMachineBuilder<States, Events, Context> builder = StateMachineBuilderFactory.create();
        builder.externalTransition()
                .from(States.STATE1)
                .to(States.STATE2)
                .on(Events.EVENT1)
                .when(checkCondition())
                .perform(doAction());

        builder.internalTransition()
                .within(States.STATE2)
                .on(Events.INTERNAL_EVENT)
                .when(checkCondition())
                .perform(doAction());

        builder.externalTransition()
                .from(States.STATE2)
                .to(States.STATE1)
                .on(Events.EVENT2)
                .when(checkCondition())
                .perform(doAction());

        builder.externalTransition()
                .from(States.STATE1)
                .to(States.STATE3)
                .on(Events.EVENT3)
                .when(checkCondition())
                .perform(doAction());

        builder.externalTransitions()
                .fromAmong(States.STATE1, States.STATE2, States.STATE3)
                .to(States.STATE4)
                .on(Events.EVENT4)
                .when(checkCondition())
                .perform(doAction());

        builder.build(machineId);

        StateMachine<States, Events, Context> stateMachine = StateMachineFactory.get(machineId);
        stateMachine.showStateMachine();
        return stateMachine;
    }

		private Condition<Context> checkCondition() {
        return (ctx) -> {return true;};
    }

    private Action<States, Events, Context> doAction() {
        return (from, to, event, ctx)->{
            System.out.println(ctx.operator+" is operating "+ctx.entityId+" from:"+from+" to:"+to+" on:"+event);
        };
    }

		@Test
    public void testExternalInternalNormal(){
        StateMachine<States, Events, Context> stateMachine = buildStateMachine("testExternalInternalNormal");

        Context context = new Context();
        States target = stateMachine.fireEvent(States.STATE1, Events.EVENT1, context);
        Assert.assertEquals(States.STATE2, target);
        target = stateMachine.fireEvent(States.STATE2, Events.INTERNAL_EVENT, context);
        Assert.assertEquals(States.STATE2, target);
        target = stateMachine.fireEvent(States.STATE2, Events.EVENT2, context);
        Assert.assertEquals(States.STATE1, target);
        target = stateMachine.fireEvent(States.STATE1, Events.EVENT3, context);
        Assert.assertEquals(States.STATE3, target);
    }
```

## 参考

https://blog.csdn.net/significantfrank/article/details/104996419