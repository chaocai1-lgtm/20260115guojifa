import json

# 读取JSON文件
with open('国际法知识图谱.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 添加根节点
root_node = {
    "id": "root",
    "label": "国际法知识图谱",
    "category": "核心问题",
    "type": "知识体系",
    "level": 0,
    "description": "国际法知识体系的中心枢纽，8大核心问题围绕展开",
    "properties": {
        "课程": "国际法",
        "学时": "54学时",
        "总体": "基于问题驱动的知识体系重构",
        "结构": "1个中心+8大核心问题+多层次知识节点"
    }
}

# 插入到节点列表的最前面
data['nodes'].insert(0, root_node)

# 找出所有level=1的核心问题，添加它们到根节点的关系
core_questions = [n for n in data['nodes'] if n.get('level') == 1 and n.get('id') != 'root']

# 为每个核心问题添加与根节点的关系
for q in core_questions:
    new_relationship = {
        "source": "root",
        "target": q['id'],
        "type": "包含",
        "description": f"国际法知识体系的组成部分"
    }
    data['relationships'].insert(0, new_relationship)

# 保存修改后的JSON
with open('国际法知识图谱.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ 根节点已添加")
print(f"   节点ID: root")
print(f"   节点标签: 国际法知识图谱")
print(f"   共添加{len(core_questions)}条关系")
print(f"✅ JSON文件已更新")
print(f"   总节点数: {len(data['nodes'])}")
print(f"   总关系数: {len(data['relationships'])}")
