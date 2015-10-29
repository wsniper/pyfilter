"""字段过滤/别名替换/默认值赋值/有效性检测

@Author： Sniper
@Contact： 81185001@163.com

功能：验证dict格式字段(如：web提交的)是否合法
规则： 
    1. 内置规则： 数据库字段定义。sql字段规则转换成范围（整数）及正则
    2. 用户自定义规则： 格式同内置规则。自定义规则可覆盖内置规则
当前实现(2015-10-27):
    只使用用户自定义规则。
"""
import re
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String
from sqlalchemy import func

# Exception
class FilterRuleValueError(Exception):
    """ 本字段出现在 FILTER_RULE 中，但是bool(rule) == False """

    def __init__(self, errobj):
        self.obj = errobj

class Filter(object):
    """字段过滤/别名替换/默认值赋值/有效性检测

    >> 功能 <<：
        1. 检测必选字段。若必选字段在data中不全则返回错误信息
        2. 字段别名替换。将别名替换为数据表定义名称
        3. 默认值赋值。 若字段值为空则赋默认值
        4. 字段有效性检测。使用正则表达式检测

    >> 调用方法 <<：
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
        
    >> 返回值 <<：
        1. 验证失败（不通过）： 
            data := {'ok':False, data: {'alias': errmsg, 'alias2': errmsg2} 
        2. 验证成功：
            data := {'ok':True, data: {'realname': val, 'realname2': val2} 
    >> 异常：
        FilterRuleValueError(obj): 规则参数值错误：
        说明： obj为 FILTER_RULE/ALIAS 的值

    >> 格式
        1.待测数据 
            data := {'field':val1, 'field':val2}
        2.规则定义
            FILTER_RULE := {'field1':rule1*, 'field2':rule2}
                rule1* := {'regex':rule, 'require':True, 'default':default_val, 'errmsg':errmsg}
        3.字段映射（别名）
                ALIAS := {'aliasname' : 'realname'}
    """

    # sqlalchemy 所有Column 对应的检测规则
    DEFAULT_RULE = {}
    FILTER_RULE = {}
    ALIAS = {}

    def __init__(self):
        # 别名字典翻转。目的是错误信息能够引用待测数据中的别名
        self.alias_reverse = {}
        for alias, realname in self.ALIAS.items():
            if not realname:
                raise FilterRuleValueError(self.ALIAS)
            self.alias_reverse[realname] = alias

    def __call__(self, data={}, n=None):
        """主方法
        字段映射（别名替换)
        检测（正则匹配）
        成功则返回格式化数据用于后续操作
        失败则返回错误信息辞典
        """
        data = data if data else {}
        rule = self.get_allrule(self.DEFAULT_RULE, self.FILTER_RULE)
        return self.check(self.get_realfname(data, self.ALIAS), rule)

    def get_allrule(self, DEFAULT_RULE={}, user_rule={}):
        """ 合并用户定义和默认规则 """

        return self.dictextend(DEFAULT_RULE, user_rule)
        
    def get_realfname(self, data={}, alias={}):
        """ 字段别名转换成数据库字段名（若有的话） 
        查别名表（在用户类定义的类属性--dict）
        """
        alias = alias if alias else {}
        if not alias:
            return data

        data = data if data else {}
        realname = {}
        for name, val in data.items():
            key = alias[name] if name in alias else name
            realname[key] = val

        return realname

    def check(self, data={}, rule={}):
        """ 检测 
            1. 必填字段是否全部在
            2. 单条数据是否合法
        """
        errdata = {'ok':False, 'data':{}}
        validdata = {'ok':True, 'data':{}}

        # 取用户定义的（本数据表）的必填字段
        require = []
        for name, val in rule.items():
            # 默认值赋值
            if name in data and not data[name] and val.get('default', None):
                data[name] = val['default']
            require.append(name) if val.get('require', None) else None

        # 必填字段是否都在
        flost = set(require) - set(data)
        if flost and require:
            for name in flost:
                errdata['data'][name] = rule[name].get('errmsg', None)
            return errdata

        # 逐条验证（必填都在的话）
        for name, val in data.items():
            if name in rule:
                if rule[name].get('regex', None):
                    m = re.fullmatch(re.compile(rule[name].get('regex', None)), str(val))
                else:
                    raise FilterRuleValueError(dict(name=val))
                if not m:
                    # 这里的name需要替换为alias
                    # 方便调用者在使用alias时调试和在前端使用
                    alias = self.alias_reverse.get(name, name)
                    errdata['data'][alias] = rule[name].get('errmsg', None)
                else:
                    validdata['data'][name] = val

        return errdata if errdata['data'] else validdata
                
    def dictextend(self, dest:dict, src:dict)->dict:
        """ 深度合并dict （多层dict）
        src覆盖同名dest的item
        """
        for k, v in src.items():
            if not v:
                return
            elif (k not in dest or 
                  not isinstance(dest[k], dict) and 
                  not isinstance(v, dict)):
                dest[k] = v
            else:
                self.dictextend(dest[k], v)
        return dest
