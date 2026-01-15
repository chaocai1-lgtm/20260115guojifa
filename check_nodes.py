import json

with open('国际法知识图谱.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 获取8个核心问题（level=1的节点）
core_questions = [n for n in data['nodes'] if n.get('level') == 1 and n.get('category') == '核心问题']
core_questions = sorted(core_questions, key=lambda x: x['id'])

print('=== 核心问题与子节点统计 ===\n')
total_nodes = 0

for q in core_questions:
    q_id = q['id']
    
    # 找所有与该问题相关的节点（递归）
    related_nodes = {q_id}
    
    def add_children(node_id):
        for rel in data['relationships']:
            if rel['source'] == node_id and rel['target'] not in related_nodes:
                related_nodes.add(rel['target'])
                add_children(rel['target'])
    
    add_children(q_id)
    
    child_count = len(related_nodes) - 1
    total_nodes += child_count
    
    # 获取直接子节点
    direct_children = [rel['target'] for rel in data['relationships'] if rel['source'] == q_id]
    
    print(f"{q['label']}")
    print(f"  总子节点: {child_count}")
    print(f"  直接连接: {len(direct_children)}")
    
    if direct_children:
        for child_id in direct_children[:3]:
            child_node = next((n for n in data['nodes'] if n['id'] == child_id), None)
            if child_node:
                print(f"    • {child_node['label']} ({child_node.get('type', 'Unknown')})")
        if len(direct_children) > 3:
            print(f"    ... 还有 {len(direct_children)-3} 个")
    print()

print(f"总知识节点数: {len(data['nodes'])}")
print(f"总关系数: {len(data['relationships'])}")
