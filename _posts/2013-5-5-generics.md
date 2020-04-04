---
date: 2013-5-5
layout: default
title: 宏与泛型与继承

---

# 泛型与继承的区别

将类型参数化，解决处理相同逻辑不同类型的需求

## 用法

泛型的最初动机:建立通用标准容器库\通用算法  
实现通用标准容器库的几种方法:继承\泛型\宏

## 用途
算法重用,函数重用,无须重载  

当遇到以下场景时，我们可以考虑使用泛型：

- 当参数类型不明确，可能会扩展为多种时。
- 想声明参数类型为 `Object`，并在使用时用 `instanceof` 判断时。

```java
    public static  <T extends Comparable<T>> void quickSort(T[] data, int start, int end) {
        T key = data[start];
        int i = start;
        int j = end;
        while (i < j) {
            while (data[j].compareTo(key) > 0 && j > i) {
                j--;
            }
            data[i] = data[j];

            while (data[i].compareTo(key) < 0 && i < j) {
                i++;
            }
            data[j] = data[i];
        }
        data[i] = key;

        if (i - 1 > start) {
            quickSort(data, start, i - 1);
        }
        if (i + 1 < end) {
            quickSort(data, i + 1, end);
        }
    }
```

## 笔记

宏是在预处理阶段进行文本替换,没有类型检查

## 使用

```java
 class Generics<T> { // 在类名后声明引入泛型类型
        private T field;  // 引入后可以将字段声明为泛型类型

        public T getField() { // 类方法内也可以使用泛型类型
            return field;
        }
    }
```

```java
 public [static] <T> void testMethod(T arg) { // 访问限定符[静态方法在 static] 后使用 <占位符> 声明泛型方法后，在参数列表后就可以使用泛型类型了
        // doSomething
    }
```

## 类型擦除

严格来说，Java的泛型并不是真正的泛型。Java 的泛型是 JDK1.5 之后添加的特性，为了兼容之前版本的代码，其实现引入了类型擦除的概念。

类型擦除指的是：Java 的泛型代码在编译时，由编译器进行类型检查，之后会将其泛型类型擦除掉，只保存原生类型，如 `Generics` 被擦除后是 `Generics`，我们常用的 `List` 被擦除后只剩下 `List`。

1. 编译期间编译器检查传入的泛型类型与声明的泛型类型是否匹配，不匹配则报出编译器错误；
2. 编译器执行类型擦除，字节码内只保留其原始类型；
3. 运行期间，再将 Object 转换为所需要的泛型类型。

`Java 的泛型实际上是由编译器实现的，将泛型类型转换为 Object 类型，在运行期间再进行状态转换`。



实现泛型时声明的具体类型必须为 Object 的子类型，这是因为编译器进行类型擦除后会使用 Object 替换泛型类型，并在运行期间进行类型转换，而基础类型和 Object 之间是无法替换和转换的

## reference

https://zhenbianshu.github.io/2018/05/java_senior_featrue_generics.html

