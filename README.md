# pyfilter
用python实现的 [字段过滤/别名替换/默认值赋值/有效性检测] 典型应用是网站post数据过滤检测。
# 简介
功能很简单，看代码即可使用。                                                                                                                              
1. 检测必选字段。若必选字段在data中不全则返回错误信息                                                                
2. 字段别名替换。将别名替换为数据定义名称                                                                          
3.  默认值赋值。 若字段值为空则赋默认值     
4.  字段有效性检测。使用正则表达式检测   

# 使用
        1. 定义子类
         | class UserFilter(Filter):
         |     FILTER_RULE = {
         |         'real_name': {
         |             'require': True
         |             'regex': '\d*'
         |             'default': 999
         |             'errmsg': '必填。数字'
         |         },
         |         'real_name_2': ...
         |         ...
         |     }
         |     ALIAS = {
         |         'alias': 'real_name',
         |         'alias2': 'real_name_2',
         |         ...
         |     }
         | 说明：
         |    # FILTER_RULE/ALIAS必须大写
         |    # FILTER_RULE/ALIAS 都是可选的
         |    # require/regex/default/errmsg全部小写。可写其中几个
         |    # real_name* 是数据库中真实字段名称
         |    # alias* 是自定义字段名。如：web表单中可使用别名来提交数据
        2. 实例化子类
         | uFilter = UserFilter()
        3. 调用子类实例并传入数据
         | filtedData = uFilter(data)
        注： 
            1. 实例化时不传入任何东西
            2. 实例化的子类可多次调用（因为有__call__）
