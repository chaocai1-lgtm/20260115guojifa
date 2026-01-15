"""
国际法知识图谱系统
基于 Streamlit（前端）与 Neo4j（后端）构建
功能：学生端浏览知识图谱，管理端查看访问数据
8大核心问题导向的国际法知识体系
"""
import streamlit as st
import streamlit.components.v1 as components
import json
import os
import pandas as pd
from datetime import datetime
from neo4j import GraphDatabase
from pyvis.network import Network
import hashlib
import time
from streamlit_javascript import st_javascript

# ==================== 配置区 ====================
# 1. 专属标签 (通过修改这个后缀，区分不同的课程)
TARGET_LABEL = "InternationalLaw"

# 2. 管理员密码
ADMIN_PASSWORD = "admin888"

# 3. 数据库配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "wE7pV36hqNSo43mpbjTlfzE7n99NWcYABDFqUGvgSrk"

# 4. JSON文件路径
current_dir = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(current_dir, "国际法知识图谱.json")
INTERACTIONS_FILE = os.path.join(current_dir, "interactions_log.json")

# ==================== 颜色配置 ====================
CATEGORY_COLORS = {
    "核心问题": "#FF6B6B",      # 红色 - 8大核心问题
    "理论基础": "#4ECDC4",      # 青色 - 理论
    "中国实践": "#FFD93D",      # 金色 - 中国贡献
    "典型案例": "#95E1D3",      # 浅绿 - 案例分析
    "法律文本": "#A8DADC"       # 浅蓝 - 重要公约
}

# 将node的type字段映射到5个主要分类
TYPE_TO_CATEGORY = {
    # 理论基础类
    "问题导向": "理论基础",
    "理论基础": "理论基础",
    "基本规则": "理论基础",
    "最高规范": "理论基础",
    "主体资格": "理论基础",
    "国家要素": "理论基础",
    "国家关系": "理论基础",
    "法律形式": "理论基础",
    "条约基础": "理论基础",
    "条约程序": "理论基础",
    "缔约技巧": "理论基础",
    "条约消灭": "理论基础",
    "国际标准": "理论基础",
    "人权保护": "理论基础",
    "个人身份": "理论基础",
    "刑事合作": "理论基础",
    "外交组织": "理论基础",
    "外交核心": "理论基础",
    "领事制度": "理论基础",
    "强行法规则": "理论基础",
    "合法武力": "理论基础",
    "解决方法": "理论基础",
    "海洋法": "理论基础",
    "海洋法核心": "理论基础",
    "海洋制度": "理论基础",
    "适用规则": "理论基础",
    
    # 中国实践类
    "中国贡献": "中国实践",
    "中国实践": "中国实践",
    "中国智慧": "中国实践",
    "理论创新": "中国实践",
    
    # 典型案例类
    "典型案例": "典型案例",
    "经典判例": "典型案例",
    "历史人物": "典型案例",
    "现实问题": "典型案例",
    "法律争议": "典型案例",
}

# 核心问题的特殊样式（第一级节点）
CORE_QUESTION_COLOR = "#FF6B6B"
CORE_QUESTION_SIZE = 60

# 根节点的特殊样式（最高级节点）
ROOT_NODE_COLOR = "#9B59B6"      # 紫色 - 最核心的中心点
ROOT_NODE_SIZE = 80

# ==================== Neo4j 数据库操作类 ====================
class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
        except Exception as e:
            # Neo4j连接失败时静默处理，系统将使用纯JSON模式运行
            self.driver = None
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def execute_query(self, query, parameters=None):
        if not self.driver:
            return []
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def execute_write(self, query, parameters=None):
        if not self.driver:
            return None
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return result.consume()

# ==================== 数据初始化 ====================
def clear_all_data(conn):
    """清除所有图形和数据（包括知识图谱和交互记录）"""
    if not conn.driver:
        return False
    
    try:
        # 清除知识图谱节点
        conn.execute_write(f"MATCH (n:{TARGET_LABEL}) DETACH DELETE n")
        # 清除交互记录
        conn.execute_write(f"MATCH (i:Interaction_{TARGET_LABEL}) DELETE i")
        st.success("✅ 数据库清除成功")
        return True
    except Exception as e:
        st.error(f"❌ 数据库清除失败: {e}")
        return False

def clear_local_files():
    """清除本地文件"""
    try:
        if os.path.exists(INTERACTIONS_FILE):
            os.remove(INTERACTIONS_FILE)
            st.success("✅ 本地交互记录清除成功")
        else:
            st.info("ℹ️ 本地文件不存在，无需清除")
        return True
    except Exception as e:
        st.error(f"❌ 本地文件清除失败: {e}")
        return False

def init_neo4j_data(conn, json_data):
    """将JSON数据导入Neo4j"""
    if not conn.driver:
        return False
    
    # 清除旧数据
    conn.execute_write(f"MATCH (n:{TARGET_LABEL}) DETACH DELETE n")
    
    # 创建节点
    for node in json_data.get("nodes", []):
        properties_json = json.dumps(node.get("properties", {}), ensure_ascii=False)
        query = f"""
        CREATE (n:{TARGET_LABEL} {{
            id: $id,
            label: $label,
            category: $category,
            type: $type,
            level: $level,
            description: $description,
            properties: $properties
        }})
        """
        conn.execute_write(query, {
            "id": node["id"],
            "label": node["label"],
            "category": node.get("category", ""),
            "type": node.get("type", ""),
            "level": node.get("level", 1),
            "description": node.get("description", ""),
            "properties": properties_json
        })
    
    # 创建关系
    for rel in json_data.get("relationships", []):
        query = f"""
        MATCH (a:{TARGET_LABEL} {{id: $source}})
        MATCH (b:{TARGET_LABEL} {{id: $target}})
        CREATE (a)-[r:RELATES {{type: $type, description: $description}}]->(b)
        """
        conn.execute_write(query, {
            "source": rel["source"],
            "target": rel["target"],
            "type": rel.get("type", "关联"),
            "description": rel.get("description", "")
        })
    
    return True

def init_interaction_table(conn):
    """初始化交互记录表（在Neo4j中创建约束）"""
    if not conn.driver:
        return
    try:
        # 创建唯一性约束
        conn.execute_write(f"CREATE CONSTRAINT IF NOT EXISTS FOR (i:Interaction_{TARGET_LABEL}) REQUIRE i.id IS UNIQUE")
    except:
        pass

def record_interaction(conn, student_id, node_id, node_label, action_type="view", duration=0):
    """记录学生交互行为（支持Neo4j和本地文件双模式）"""
    timestamp = datetime.now()
    
    # 尝试记录到Neo4j
    if conn.driver:
        try:
            query = f"""
            CREATE (i:Interaction_{TARGET_LABEL} {{
                id: $id,
                student_id: $student_id,
                node_id: $node_id,
                node_label: $node_label,
                action_type: $action_type,
                duration: $duration,
                timestamp: datetime($timestamp)
            }})
            """
            interaction_id = f"{student_id}_{node_id}_{timestamp.strftime('%Y%m%d%H%M%S%f')}"
            conn.execute_write(query, {
                "id": interaction_id,
                "student_id": student_id,
                "node_id": node_id,
                "node_label": node_label,
                "action_type": action_type,
                "duration": duration,
                "timestamp": timestamp.isoformat()
            })
        except Exception as e:
            st.warning(f"Neo4j记录失败: {e}")
    
    # 同时记录到本地文件（作为备份或在无Neo4j时使用）
    try:
        interactions = []
        if os.path.exists(INTERACTIONS_FILE):
            with open(INTERACTIONS_FILE, "r", encoding="utf-8") as f:
                interactions = json.load(f)
        
        interactions.append({
            "student_id": student_id,
            "node_id": node_id,
            "node_label": node_label,
            "action_type": action_type,
            "duration": duration,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        with open(INTERACTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(interactions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"本地文件记录失败: {e}")

def get_all_interactions(conn):
    """获取所有交互记录（优先从Neo4j，否则从本地文件）"""
    # 尝试从Neo4j获取
    if conn.driver:
        try:
            query = f"""
            MATCH (i:Interaction_{TARGET_LABEL})
            RETURN i.student_id as student_id,
                   i.node_id as node_id,
                   i.node_label as node_label,
                   i.action_type as action_type,
                   i.duration as duration,
                   toString(i.timestamp) as timestamp
            ORDER BY i.timestamp DESC
            """
            return conn.execute_query(query)
        except:
            pass
    
    # 从本地文件获取
    try:
        if os.path.exists(INTERACTIONS_FILE):
            with open(INTERACTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    
    return []

# ==================== 加载JSON数据 ====================
@st.cache_data
def load_json_data():
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"❌ 无法加载知识图谱数据: {e}")
        return {"nodes": [], "relationships": []}

# ==================== 创建知识图谱可视化 ====================
def create_knowledge_graph(json_data, selected_question=None, selected_node=None):
    """创建交互式知识图谱，支持按问题筛选"""
    net = Network(height="1350px", width="100%", bgcolor="#ffffff", font_color="#333333")
    net.barnes_hut(gravity=-2500, central_gravity=0.2, spring_length=250)
    
    # 如果选定了问题，只显示该问题及其2级子节点
    if selected_question:
        question_id = selected_question["id"]
        # 找出所有与该问题相关的节点（最多2级深度）
        filtered_nodes = {question_id}  # 先加入问题本身
        visited = set()  # 记录已访问的节点，避免重复遍历
        
        # 递归找出2级子节点（双向遍历）
        def add_children_limited(node_id, relationships, depth=1, max_depth=2):
            if depth > max_depth or node_id in visited:
                return
            visited.add(node_id)
            
            for rel in relationships:
                other_node_id = None
                # 双向处理：既看source->target，也看target->source
                if rel["source"] == node_id:
                    other_node_id = rel["target"]
                elif rel["target"] == node_id:
                    other_node_id = rel["source"]
                
                if other_node_id and other_node_id not in filtered_nodes:
                    filtered_nodes.add(other_node_id)
                    add_children_limited(other_node_id, relationships, depth + 1, max_depth)
        
        add_children_limited(question_id, json_data.get("relationships", []))
        
        # 过滤节点和边
        display_nodes = [n for n in json_data.get("nodes", []) if n["id"] in filtered_nodes]
        display_relationships = [r for r in json_data.get("relationships", []) 
                                if r["source"] in filtered_nodes and r["target"] in filtered_nodes]
    else:
        # 显示所有节点
        display_nodes = json_data.get("nodes", [])
        display_relationships = json_data.get("relationships", [])
    
    # 添加节点
    for node in display_nodes:
        # 根节点（level=0）使用最特殊的颜色和大小
        if node.get("level") == 0:
            color = ROOT_NODE_COLOR
            size = ROOT_NODE_SIZE
        # 核心问题（level=1）使用特殊颜色和大小
        elif node.get("level") == 1 and node.get("category") == "核心问题":
            color = CORE_QUESTION_COLOR
            size = CORE_QUESTION_SIZE
        else:
            # 其他节点根据type字段映射到分类，然后获取颜色
            node_type = node.get("type", "Unknown")
            mapped_category = TYPE_TO_CATEGORY.get(node_type, "理论基础")  # 默认映射到理论基础
            color = CATEGORY_COLORS.get(mapped_category, "#888888")
            size = (40 - (node.get("level", 1) - 1) * 5) * 2
        
        # 如果是选中的节点，增加边框
        border_width = 5 if selected_node == node["id"] else 3 if node.get("level") == 1 else 2
        
        net.add_node(
            node["id"],
            label=node["label"],
            color=color,
            size=size,
            title=node["label"] + " (" + node["category"] + ")",
            borderWidth=border_width,
            borderWidthSelected=5,
            font={"size": 160, "color": "#222222", "face": "Microsoft YaHei, SimHei, sans-serif", "bold": True}
        )
    
    # 添加边
    for rel in display_relationships:
        net.add_edge(
            rel["source"],
            rel["target"],
            title=rel.get("type", "关联"),
            label=rel.get("type", ""),
            color="#999999",
            width=1,
            arrows={"to": {"enabled": True, "scaleFactor": 0.3}},
            font={"size": 20, "color": "#555"}
        )
    
    # 配置交互选项 - 稳定后禁用物理引擎，节点可自由拖动
    net.set_options("""
    {
        "nodes": {
            "font": {
                "size": 20,
                "face": "Microsoft YaHei, SimHei, sans-serif"
            }
        },
        "edges": {
            "smooth": false,
            "width": 1,
            "color": "#999999"
        },
        "interaction": {
            "hover": true,
            "navigationButtons": false,
            "keyboard": true,
            "dragNodes": true,
            "dragView": true,
            "zoomView": true
        },
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -6000,
                "centralGravity": 0.15,
                "springLength": 400,
                "springConstant": 0.008,
                "avoidOverlap": 0.8
            },
            "stabilization": {
                "enabled": true,
                "iterations": 400,
                "fit": true
            }
        }
    }
    """)
    
    # 为图谱添加拖动事件监听：当拖动核心问题节点时，其子节点跟随移动
    # 构建节点关系映射：每个节点 -> 其所有子节点
    node_children = {}
    for rel in display_relationships:
        source = rel["source"]
        target = rel["target"]
        if source not in node_children:
            node_children[source] = []
        node_children[source].append(target)
    
    # 在HTML中添加JavaScript代码，处理拖动事件
    drag_script = f"""
    <script type="text/javascript">
    // 构建节点关系映射
    var nodeChildren = {json.dumps(node_children)};
    var draggedNode = null;
    var dragOffset = {{}};
    
    // 等待network对象准备好，然后监听拖动事件
    function setupDragListener() {{
        if (typeof network === 'undefined') {{
            setTimeout(setupDragListener, 100);
            return;
        }}
        
        network.on("dragStart", function(params) {{
            if (params.nodes.length > 0) {{
                draggedNode = params.nodes[0];
                try {{
                    var pos = network.getPositions([draggedNode])[draggedNode];
                    dragOffset.x = pos.x;
                    dragOffset.y = pos.y;
                }} catch(e) {{
                    draggedNode = null;
                }}
            }}
        }});
        
        network.on("dragging", function(params) {{
            if (draggedNode && nodeChildren[draggedNode]) {{
                try {{
                    // 获取被拖动节点的当前位置
                    var currentPos = network.getPositions([draggedNode])[draggedNode];
                    var dx = currentPos.x - dragOffset.x;
                    var dy = currentPos.y - dragOffset.y;
                    
                    if (Math.abs(dx) < 0.1 && Math.abs(dy) < 0.1) return;
                    
                    // 移动所有子节点
                    var childrenToUpdate = {{}};
                    var processedNodes = {{}};
                    
                    function moveChildren(parentId) {{
                        if (nodeChildren[parentId]) {{
                            nodeChildren[parentId].forEach(function(childId) {{
                                if (!processedNodes[childId]) {{
                                    processedNodes[childId] = true;
                                    try {{
                                        var childPos = network.getPositions([childId])[childId];
                                        childrenToUpdate[childId] = {{
                                            x: childPos.x + dx,
                                            y: childPos.y + dy
                                        }};
                                        // 递归移动子节点的子节点
                                        moveChildren(childId);
                                    }} catch(e) {{
                                        // 忽略错误，继续处理其他节点
                                    }}
                                }}
                            }});
                        }}
                    }}
                    
                    moveChildren(draggedNode);
                    
                    // 更新所有子节点位置
                    if (Object.keys(childrenToUpdate).length > 0) {{
                        network.setOptions({{physics: {{enabled: false}}}});
                        network.setPositions(childrenToUpdate);
                    }}
                    
                    // 更新记录的偏移
                    dragOffset.x = currentPos.x;
                    dragOffset.y = currentPos.y;
                }} catch(e) {{
                    console.warn("拖动处理错误:", e);
                }}
            }}
        }});
        
        network.on("dragEnd", function(params) {{
            draggedNode = null;
            // 拖动结束后不重新启用物理引擎，保持节点在拖动的位置
            // 这样可以避免拖动后还有自动调整的动画效果
            // 如果需要完全重新计算布局，可以手动刷新页面
        }});
    }}
    
    // 初始化监听
    setupDragListener();
    </script>
    """
    
    return net, drag_script

# ==================== 信息卡片组件 ====================
def render_info_card(node_data):
    """渲染节点信息卡片"""
    color = CATEGORY_COLORS.get(node_data["category"], "#888888")
    
    st.markdown(f"""
    <div style='
        background: #ffffff;
        border-left: 4px solid {color};
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    '>
        <h3 style='color: {color}; margin-bottom: 10px;'>📌 {node_data["label"]}</h3>
        <div style='display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px;'>
            <span style='background: {color}22; color: {color}; padding: 4px 10px; border-radius: 15px; font-size: 12px;'>
                {node_data["category"]}
            </span>
            <span style='background: #f0f0f0; color: #666; padding: 4px 10px; border-radius: 15px; font-size: 12px;'>
                {node_data["type"]}
            </span>
            <span style='background: #f0f0f0; color: #666; padding: 4px 10px; border-radius: 15px; font-size: 12px;'>
                层级 {node_data["level"]}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 属性详情
    st.markdown("✅ **详细信息**")
    properties = node_data.get("properties", {})
    
    if properties:
        # 将properties转换为可显示的格式
        if isinstance(properties, str):
            try:
                properties = json.loads(properties)
            except:
                properties = {}
        
        for key, value in properties.items():
            if value and value != "":
                st.markdown(f"""
                <div style='
                    background: #f8f9fa;
                    border-radius: 8px;
                    padding: 10px 12px;
                    margin: 6px 0;
                    border-left: 3px solid {color};
                '>
                    <span style='color: {color}; font-weight: bold; font-size: 13px;'>{key}</span>
                    <p style='color: #333; margin: 4px 0 0 0; font-size: 13px; line-height: 1.5;'>{value}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("暂无详细属性信息")

# ==================== 学生端页面 ====================
def student_page(conn, json_data):
    """学生端：浏览知识图谱"""
    
    # 获取所有8个核心问题（level=1）
    core_questions = [node for node in json_data.get("nodes", []) 
                     if node.get("level") == 1 and node.get("category") == "核心问题"]
    core_questions = sorted(core_questions, key=lambda x: x.get("id"))
    
    # ========== 左侧侧边栏：问题菜单、知识分类和节点详情 ==========
    with st.sidebar:
        
        # 学生登录（可选）
        with st.expander("👤 学生登录（可选）", expanded=False):
            login_input = st.text_input("学号或姓名", value=st.session_state.get("login_input", ""), key="login_input_field")
            
            if st.button("确认登录", type="primary", use_container_width=True):
                if login_input:
                    st.session_state.login_input = login_input
                    st.session_state.student_id = login_input
                    st.success(f"欢迎, {login_input}!")
                else:
                    st.warning("请输入学号或姓名")
            
            if st.session_state.get("student_id"):
                st.markdown(f"✅ 已登录: **{st.session_state.student_id}**")
        
        st.markdown("---")
        
        # 知识分类（多列布局） - 放在上方
        st.markdown("### 📊 知识分类")
        cols = st.columns(2)  # 分成2列
        for idx, (cat, color) in enumerate(CATEGORY_COLORS.items()):
            col = cols[idx % 2]
            with col:
                st.markdown(
                    f"<div style='background:{color}20;border-left:4px solid {color};padding:8px;margin:6px 0;border-radius:4px;'>"
                    f"<span style='color:{color};font-weight:bold;font-size:13px;'>{cat}</span></div>",
                    unsafe_allow_html=True
                )
        
        st.markdown("---")
        
        # 8大核心问题菜单
        st.markdown("### 📚 8大核心问题")
        
        selected_question = st.radio(
            "选择问题",
            options=[None] + core_questions,
            format_func=lambda x: "📖 查看全图" if x is None else x.get("label", ""),
            label_visibility="collapsed"
        )
        
        st.session_state.selected_question = selected_question
        if selected_question:
            st.markdown(f"#### 📌 {selected_question['label']}")
        
        st.markdown("---")
        st.markdown("💡 **提示**: 点击图谱中的节点查看详情")
        
        # 读取并处理localStorage中的交互记录
        if st.session_state.get("student_id"):
            try:
                interactions_js = st_javascript("""
                    var interactions = localStorage.getItem('pending_interactions');
                    if (interactions) {
                        localStorage.removeItem('pending_interactions');
                        interactions;
                    } else {
                        null;
                    }
                """, key=f"read_interactions_{int(time.time())}")
                
                if interactions_js:
                    import json as json_lib
                    try:
                        interactions_list = json_lib.loads(interactions_js)
                        for interaction in interactions_list:
                            record_interaction(
                                conn,
                                st.session_state.student_id,
                                interaction.get('node_id', ''),
                                interaction.get('node_label', ''),
                                'view',
                                0
                            )
                    except:
                        pass
            except:
                pass
        
            # 显示选中节点的详情
            if st.session_state.get("selected_node"):
                st.markdown("---")
                st.markdown("### 📍 节点详情")
                render_info_card(st.session_state.selected_node)
    
    # ========== 主区域 ==========
    st.title("⚖️ 国际法知识图谱")
    st.markdown("基于8大核心问题的国际法知识体系重构")
    
    st.markdown("---")
    
    # ========== 知识图谱（全宽显示）==========
    
    # 获取URL参数中的选中节点，用于高亮显示
    query_params = st.query_params
    url_selected = query_params.get("selected_node", None)
    
    # 创建并显示图谱（传入选定的问题）
    net, drag_script = create_knowledge_graph(json_data, st.session_state.get("selected_question"), url_selected)
    
    # 保存并显示HTML
    graph_path = os.path.join(current_dir, "temp_graph.html")
    net.save_graph(graph_path)
    
    # 读取并嵌入HTML
    with open(graph_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # 准备节点数据供 JavaScript 使用
    nodes_data = {node["id"]: node for node in json_data.get("nodes", [])}
    nodes_json = json.dumps(nodes_data, ensure_ascii=False)
    
    # 准备边的数据供高亮使用
    edges_data = json_data.get("relationships", [])
    edges_json = json.dumps(edges_data, ensure_ascii=False)
    
    # 注入点击事件处理
    click_handler = f"""
    <style>
    html, body {{
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        overflow: hidden !important;
    }}
    #mynetwork {{
        border: none !important;
        outline: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }}
    #node-detail-panel {{
        position: fixed;
        top: 20px;
        right: 20px;
        width: 400px;
        max-height: 85vh;
        background: rgba(255,255,255,0.98);
        padding: 25px;
        z-index: 9999;
        overflow-y: auto;
        display: none;
        font-family: 'Microsoft YaHei', sans-serif;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        border-radius: 15px;
        border: 2px solid #e0e0e0;
    }}
    #node-detail-panel h3 {{
        margin: 0 0 15px 0;
        color: #1976d2;
        font-size: 20px;
        padding-bottom: 10px;
        border-bottom: 3px solid #1976d2;
    }}
    #node-detail-panel .detail-row {{
        margin: 10px 0;
        font-size: 14px;
        line-height: 1.8;
        padding: 8px;
        background: #f5f5f5;
        border-radius: 5px;
    }}
    #node-detail-panel .detail-label {{
        font-weight: bold;
        color: #333;
    }}
    #node-detail-panel .detail-value {{
        color: #555;
    }}
    #node-detail-panel .close-btn {{
        position: absolute;
        top: 15px;
        right: 20px;
        cursor: pointer;
        font-size: 28px;
        color: #999;
        transition: color 0.3s;
    }}
    #node-detail-panel .close-btn:hover {{
        color: #f44336;
    }}
    #node-detail-panel .relations-section {{
        margin-top: 20px;
        padding-top: 15px;
        border-top: 2px solid #e0e0e0;
    }}
    #node-detail-panel .relations-section h4 {{
        margin: 0 0 10px 0;
        color: #666;
        font-size: 16px;
    }}
    #node-detail-panel .relation-item {{
        margin: 6px 0;
        font-size: 13px;
        color: #555;
        padding: 6px;
        background: #e3f2fd;
        border-radius: 4px;
    }}
    </style>
    
    <div id="node-detail-panel">
        <span class="close-btn" onclick="closeDetailPanel()">✕</span>
        <h3 id="detail-title">节点详情</h3>
        <div id="detail-content"></div>
        <div id="relations-content"></div>
    </div>
    
    <script>
    // 数据初始化
    var nodesData = {nodes_json};
    var edgesData = {edges_json};
    
    var originalColors = {{}};
    var networkRef = null;
    
    function closeDetailPanel() {{
        document.getElementById('node-detail-panel').style.display = 'none';
        if (networkRef) {{
            restoreAllColors();
        }}
    }}
    
    function restoreAllColors() {{
        if (!networkRef) return;
        var nodeUpdates = [];
        var edgeUpdates = [];
        
        for (var nodeId in originalColors.nodes) {{
            nodeUpdates.push({{id: nodeId, color: originalColors.nodes[nodeId], font: {{color: '#333333'}}}});
        }}
        for (var edgeId in originalColors.edges) {{
            edgeUpdates.push({{id: edgeId, color: '#999999', font: {{color: '#555'}}}});
        }}
        
        if (nodeUpdates.length > 0) {{
            networkRef.body.data.nodes.update(nodeUpdates);
        }}
        if (edgeUpdates.length > 0) {{
            networkRef.body.data.edges.update(edgeUpdates);
        }}
        originalColors = {{nodes: {{}}, edges: {{}}}};
    }}
    
    function highlightConnected(clickedNodeId) {{
        if (!networkRef) return;
        
        restoreAllColors();
        
        var connectedNodes = new Set([clickedNodeId]);
        var connectedEdgeIds = new Set();
        var visited = {{}};
        
        // 获取点击节点的信息
        var clickedNode = nodesData[clickedNodeId];
        var isClickedNodeCoreQuestion = clickedNode && clickedNode.level === 1 && clickedNode.category === '核心问题';
        
        // 递归找出2级关系的所有节点
        function findConnectedRecursive(nodeId, level) {{
            if (level > 2 || visited[nodeId]) return;
            visited[nodeId] = true;
            
            var allEdges = networkRef.body.data.edges.get();
            allEdges.forEach(function(edge) {{
                if (edge.from === nodeId || edge.to === nodeId) {{
                    var otherNodeId = edge.from === nodeId ? edge.to : edge.from;
                    var otherNode = nodesData[otherNodeId];
                    
                    // 如果点击的是核心问题，限制连接规则
                    if (isClickedNodeCoreQuestion) {{
                        // 禁止连接到其他核心问题
                        if (otherNode && otherNode.level === 1 && otherNode.category === '核心问题') {{
                            // 除非这个节点是根节点（可以经过根节点）
                            if (otherNode.level !== 0) {{
                                return;
                            }}
                        }}
                    }}
                    
                    connectedNodes.add(otherNodeId);
                    connectedEdgeIds.add(edge.id);
                    // 递归查找下一层
                    findConnectedRecursive(otherNodeId, level + 1);
                }}
            }});
        }}
        
        findConnectedRecursive(clickedNodeId, 1);
        
        var allEdges = networkRef.body.data.edges.get();
        var allNodes = networkRef.body.data.nodes.get();
        var nodeUpdates = [];
        var edgeUpdates = [];
        
        originalColors = {{nodes: {{}}, edges: {{}}}};
        
        allNodes.forEach(function(node) {{
            originalColors.nodes[node.id] = node.color;
            if (connectedNodes.has(node.id)) {{
                nodeUpdates.push({{id: node.id, font: {{color: '#000000'}}}});
            }} else {{
                nodeUpdates.push({{id: node.id, color: '#dddddd', font: {{color: '#bbbbbb'}}}});
            }}
        }});
        
        allEdges.forEach(function(edge) {{
            originalColors.edges[edge.id] = edge.color;
            if (connectedEdgeIds.has(edge.id)) {{
                edgeUpdates.push({{id: edge.id, color: '#2196F3', width: 3, font: {{color: '#2196F3'}}}});
            }} else {{
                edgeUpdates.push({{id: edge.id, color: '#eeeeee', font: {{color: '#cccccc'}}}});
            }}
        }});
        
        networkRef.body.data.nodes.update(nodeUpdates);
        networkRef.body.data.edges.update(edgeUpdates);
    }}
    
    window.onload = function() {{
        var attempts = 0;
        var maxAttempts = 20;
        
        function tryBindEvents() {{
            attempts++;
            var networkObj = null;
            
            if (typeof network !== 'undefined') {{
                networkObj = network;
            }} else if (typeof window.network !== 'undefined') {{
                networkObj = window.network;
            }}
            
            if (networkObj) {{
                networkRef = networkObj;
                
                networkObj.on('stabilized', function() {{
                    networkObj.setOptions({{physics: {{enabled: false}}}});
                }});
                
                networkObj.on('click', function(params) {{
                    if (params.nodes && params.nodes.length > 0) {{
                        var nodeId = params.nodes[0];
                        var node = nodesData[nodeId];
                        if (node) {{
                            showNodeDetail(node, nodeId);
                            highlightConnected(nodeId);
                            
                            try {{
                                var pending = localStorage.getItem('pending_interactions');
                                var interactions = pending ? JSON.parse(pending) : [];
                                interactions.push({{
                                    node_id: nodeId,
                                    node_label: node.label || nodeId,
                                    timestamp: new Date().toISOString()
                                }});
                                localStorage.setItem('pending_interactions', JSON.stringify(interactions));
                            }} catch(e) {{}}
                        }}
                    }} else {{
                        closeDetailPanel();
                    }}
                }});
            }} else if (attempts < maxAttempts) {{
                setTimeout(tryBindEvents, 300);
            }}
        }}
        
        function showNodeDetail(node, nodeId) {{
            var panel = document.getElementById('node-detail-panel');
            var title = document.getElementById('detail-title');
            var content = document.getElementById('detail-content');
            var relationsContent = document.getElementById('relations-content');
            
            title.innerText = '📍 ' + (node.label || node.id);
            
            var html = '';
            
            if (node.category) {{
                html += '<div class="detail-row"><span class="detail-label">📂 类别：</span><span class="detail-value">' + node.category + '</span></div>';
            }}
            if (node.type) {{
                html += '<div class="detail-row"><span class="detail-label">🏷️ 类型：</span><span class="detail-value">' + node.type + '</span></div>';
            }}
            if (node.description) {{
                html += '<div class="detail-row"><span class="detail-label">📝 描述：</span><span class="detail-value">' + node.description + '</span></div>';
            }}
            if (node.properties) {{
                var props = typeof node.properties === 'string' ? JSON.parse(node.properties) : node.properties;
                for (var key in props) {{
                    if (props.hasOwnProperty(key) && props[key] && props[key] !== '') {{
                        html += '<div class="detail-row"><span class="detail-label">🔹 ' + key + '：</span><span class="detail-value">' + props[key] + '</span></div>';
                    }}
                }}
            }}
            
            if (html === '') {{
                html = '<div class="detail-row"><span class="detail-label">ID：</span><span class="detail-value">' + node.id + '</span></div>';
            }}
            
            content.innerHTML = html;
            
            var relHtml = '<div class="relations-section"><h4>🔗 相关联系（2级）</h4>';
            var hasRelations = false;
            var processedRelations = {{}};
            var relationsToShow = [];
            
            // 递归找出2级关系
            function findRelationsRecursive(currentNodeId, level, visited) {{
                if (level > 2 || visited[currentNodeId]) return;
                visited[currentNodeId] = true;
                
                edgesData.forEach(function(edge) {{
                    var relKey = edge.source + '-' + edge.target + '-' + edge.type;
                    if (processedRelations[relKey]) return;
                    
                    if (edge.source === currentNodeId) {{
                        var targetNode = nodesData[edge.target];
                        var targetLabel = targetNode ? targetNode.label : edge.target;
                        var levelPrefix = level === 1 ? '➡️ ' : '└─ ';
                        relationsToShow.push({{
                            html: '<div class="relation-item" style="margin-left: ' + (level * 15) + 'px;">' + levelPrefix + '<strong>' + (edge.type || '关联') + '</strong> → ' + targetLabel + '</div>',
                            level: level
                        }});
                        processedRelations[relKey] = true;
                        findRelationsRecursive(edge.target, level + 1, visited);
                    }} else if (edge.target === currentNodeId) {{
                        var sourceNode = nodesData[edge.source];
                        var sourceLabel = sourceNode ? sourceNode.label : edge.source;
                        var levelPrefix = level === 1 ? '⬅️ ' : '└─ ';
                        relationsToShow.push({{
                            html: '<div class="relation-item" style="margin-left: ' + (level * 15) + 'px;">' + levelPrefix + sourceLabel + ' <strong>' + (edge.type || '关联') + '</strong></div>',
                            level: level
                        }});
                        processedRelations[relKey] = true;
                        findRelationsRecursive(edge.source, level + 1, visited);
                    }}
                }});
            }}
            
            findRelationsRecursive(nodeId, 1, {{}});
            
            relationsToShow.forEach(function(rel) {{
                relHtml += rel.html;
                hasRelations = true;
            }});
            
            relHtml += '</div>';
            
            relationsContent.innerHTML = hasRelations ? relHtml : '';
            panel.style.display = 'block';
        }}
        
        setTimeout(tryBindEvents, 500);
    }};
    </script>
    """
    html_content = html_content.replace("</body>", click_handler + drag_script + "</body>")
    
    components.html(html_content, height=1000, scrolling=False)

# ==================== 管理端页面 ====================
def admin_page(conn, json_data):
    """管理端：查看学生访问数据"""
    st.title("📊 管理端 - 学生学习数据分析")
    
    # 显示数据来源信息
    if conn.driver:
        st.info("📡 数据来源: Neo4j 数据库")
    else:
        st.info("📁 数据来源: 本地文件 (interactions_log.json)")
    
    # 获取所有交互数据
    interactions = get_all_interactions(conn)
    
    # 调试信息
    st.caption(f"共获取到 {len(interactions)} 条记录")
    
    if not interactions:
        st.warning("暂无学生访问数据。请先在学生端浏览知识图谱，数据会自动记录。")
        
        # 显示本地文件状态
        if os.path.exists(INTERACTIONS_FILE):
            st.info(f"✅ 本地记录文件存在: {INTERACTIONS_FILE}")
            try:
                with open(INTERACTIONS_FILE, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                    st.write(f"本地文件中有 {len(local_data)} 条记录")
                    if local_data:
                        st.dataframe(pd.DataFrame(local_data), use_container_width=True)
            except Exception as e:
                st.error(f"读取本地文件失败: {e}")
        else:
            st.warning(f"❌ 本地记录文件不存在: {INTERACTIONS_FILE}")
        
        # 提供初始化数据选项
        if conn.driver and st.button("🔄 初始化知识图谱数据到Neo4j"):
            with st.spinner("正在导入数据..."):
                if init_neo4j_data(conn, json_data):
                    init_interaction_table(conn)
                    st.success("✅ 数据初始化成功！")
                else:
                    st.error("❌ 数据初始化失败")
        return
    
    df = pd.DataFrame(interactions)
    
    # 整体统计
    st.markdown("## 📈 整体数据统计")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_visits = len(df)
        st.metric("总访问次数", total_visits)
    with col2:
        unique_students = df["student_id"].nunique()
        st.metric("学习学生数", unique_students)
    with col3:
        unique_nodes = df["node_id"].nunique()
        st.metric("被访问节点数", unique_nodes)
    with col4:
        avg_duration = df[df["duration"] > 0]["duration"].mean()
        st.metric("平均浏览时长(秒)", f"{avg_duration:.1f}" if pd.notna(avg_duration) else "N/A")
    
    st.divider()
    
    # 节点访问热度
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 🔥 节点访问热度排行")
        node_counts = df.groupby(["node_id", "node_label"]).size().reset_index(name="访问次数")
        node_counts = node_counts.sort_values("访问次数", ascending=False).head(10)
        
        st.dataframe(
            node_counts[["node_label", "访问次数"]].rename(columns={"node_label": "节点名称"}),
            use_container_width=True,
            hide_index=True
        )
    
    with col_right:
        st.markdown("### 👥 学生活跃度排行")
        student_counts = df.groupby("student_id").size().reset_index(name="访问次数")
        student_counts = student_counts.sort_values("访问次数", ascending=False).head(10)
        
        st.dataframe(
            student_counts.rename(columns={"student_id": "学号"}),
            use_container_width=True,
            hide_index=True
        )
    
    st.divider()
    
    # 类别分布
    st.markdown("### 📊 知识类别访问分布")
    
    # 合并节点类别信息
    node_categories = {node["id"]: node["category"] for node in json_data.get("nodes", [])}
    df["category"] = df["node_id"].map(node_categories)
    
    category_counts = df.groupby("category").size().reset_index(name="访问次数")
    st.bar_chart(category_counts.set_index("category")["访问次数"])
    
    st.divider()
    
    # 个人数据查询
    st.markdown("## 👤 个人学习数据查询")
    
    all_students = sorted(df["student_id"].unique().tolist())
    selected_student = st.selectbox("选择学生学号", options=all_students)
    
    if selected_student:
        student_data = df[df["student_id"] == selected_student]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("访问节点数", student_data["node_id"].nunique())
        with col2:
            st.metric("总访问次数", len(student_data))
        with col3:
            total_duration = student_data[student_data["duration"] > 0]["duration"].sum()
            st.metric("总学习时长(秒)", int(total_duration))
        
        st.markdown("#### 📜 访问记录")
        st.dataframe(
            student_data[["node_label", "action_type", "duration", "timestamp"]].rename(columns={
                "node_label": "节点名称",
                "action_type": "操作类型",
                "duration": "浏览时长(秒)",
                "timestamp": "时间"
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # 学习路径可视化
        st.markdown("#### 🛤️ 学习路径")
        path_nodes = student_data["node_label"].tolist()
        if len(path_nodes) > 1:
            path_str = " → ".join(path_nodes[:20])  # 最多显示20个
            if len(path_nodes) > 20:
                path_str += " → ..."
            st.markdown(f"```\n{path_str}\n```")
        else:
            st.info("学习路径数据不足")
    
    st.divider()
    
    # 数据管理
    st.markdown("## ⚙️ 数据管理")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 重新初始化知识图谱"):
            with st.spinner("正在重新导入数据..."):
                if init_neo4j_data(conn, json_data):
                    st.success("✅ 知识图谱数据已重新初始化")
                else:
                    st.error("❌ 初始化失败")
    
    with col2:
        if st.button("🗑️ 清除所有访问记录", type="secondary"):
            if conn.driver:
                conn.execute_write(f"MATCH (n:Interaction_{TARGET_LABEL}) DELETE n")
                st.success("✅ 访问记录已清除")
                st.rerun()
    
    with col3:
        if st.button("🆕 新建数据仓库", type="primary"):
            st.warning("⚠️ 此操作将清除所有现有数据！")
            if st.checkbox("我确认要清除所有数据并创建新仓库"):
                with st.spinner("正在清除数据..."):
                    # 清除Neo4j数据
                    if clear_all_data(conn):
                        st.success("✅ Neo4j数据已清除")
                    
                    # 清除本地文件
                    if clear_local_files():
                        st.success("✅ 本地文件已清除")
                    
                    # 创建新的空白数据仓库
                    new_data = create_new_data_warehouse()
                    if save_json_data(new_data):
                        st.success("✅ 新数据仓库已创建")
                        st.info("📝 请编辑 JSON 文件来添加节点和关系")
                        st.rerun()
                    else:
                        st.error("❌ 创建新数据仓库失败")

# ==================== 主程序入口 ====================
def main():
    st.set_page_config(
        page_title="国际法知识图谱",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 自定义CSS样式 - 白色主题
    st.markdown("""
    <style>
    .stApp {
        background: #ffffff;
    }
    .stSelectbox > div > div {
        background-color: #f8f9fa;
    }
    .stTextInput > div > div > input {
        background-color: #f8f9fa;
        color: #333;
    }
    .stButton > button {
        background: linear-gradient(90deg, #4ECDC4 0%, #45B7D1 100%);
        color: white;
        border: none;
        border-radius: 8px;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #45B7D1 0%, #4ECDC4 100%);
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #4ECDC4;
    }
    .stSidebar {
        background-color: #f8f9fa;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 加载JSON数据
    json_data = load_json_data()
    if not json_data:
        st.error("无法加载知识图谱数据，请检查JSON文件")
        return
    
    # 连接Neo4j
    conn = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    # 侧边栏导航
    st.sidebar.title("🧭 导航")
    
    page = st.sidebar.radio(
        "选择页面",
        options=["🎓 学生端", "🔐 管理端"],
        index=0
    )
    
    if page == "🎓 学生端":
        student_page(conn, json_data)
    else:
        # 管理端需要密码验证
        st.sidebar.markdown("---")
        password = st.sidebar.text_input("🔑 管理员密码", type="password")
        
        if password == ADMIN_PASSWORD:
            st.sidebar.success("✅ 验证成功")
            admin_page(conn, json_data)
        elif password:
            st.sidebar.error("❌ 密码错误")
            st.warning("请输入正确的管理员密码")
        else:
            st.info("👈 请在侧边栏输入管理员密码")
    
    # 关闭数据库连接
    conn.close()
    
    # 页脚
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='text-align: center; color: #666; font-size: 12px;'>
        <p>国际法知识图谱</p>
        <p>《国际法》课程教学资源</p>
        <p>© 2026</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
