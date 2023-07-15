# buondua-downloader

理论上支持[Buondua](https://buondua.com/)的所有页面

> 代码没整理，存在代码残留垃圾
>
> 不过无所谓，能用就行，仅作记录

## 程序大致逻辑

1. 判断是否为图集列表
   1. 获取当页所有图集的URL(可以做当前指定页面的多个page，但是我觉得没啥用，又不是要全站爬取)
   2. 调用下面的方法
2. 判断是否为图集页面
   1. 获取当前图集的所有page
   2. 调用下面的方法
3. 下载图片并记录下载失败的图片以及对应的保存位置
4. 重新下载下载失败的图片到对应的保存位置

> 所以我才说，理论上支持[Buondua](https://buondua.com/)的所有页面

## 自定义

支持在程序目录下创建`setting.yml`文件

```yaml
# 保存路径
save_path: downloads
# 最大线程数
num_threads: 5
# 下载多少个之后，进入冷却期
max_counter: 50
# 冷却期时间
wait: 10
```
> 这里填写的也就是默认值

> 原本还想添加一个允许配置User-Agent池，但是还是算了，内置了10个User-Agent

## 特点

1. 会自动根据图集名称，自动创建文件夹
   > 只适配了Windows的文件夹命名规制
   > 所有不合规的替换成`-`
   
2. 文件命名规则: ~~`{page}-{index}.{ext}`~~(我嘞个去，我把它做成了`{page}-{index}.{source_name}`)
3. 支持多种下载方式
   1. 图集ID: 31465
   2. 链接Pathname: pure-media-vol-232-onix-오닉스-hot-debut-99-photos-30151、hot
   3. 完整链接: https://buondua.com/?start=1
  
4. 多彩信息输出
   > 只有一个问题，就是不晓得咋回事，信息输出替换不稳定，有时候输出信息换行了，下一次只会把换行的部分给覆盖掉

## 截图

### 下载后自动命名

![image](https://github.com/ACG-Q/buondua-downloader/assets/47310744/4ae36766-fd08-4252-98f8-ac048310edf7)

![image](https://github.com/ACG-Q/buondua-downloader/assets/47310744/aa5d2160-ca74-4d01-b6f7-3dd3ca7de55f)

### 多彩信息输出

![image](https://github.com/ACG-Q/buondua-downloader/assets/47310744/176c8aca-44ab-4a48-bc4e-9a262e3a7899)
