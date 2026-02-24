"""
Seed demo data for HelpingHandle showcase scenarios.

Usage:
    python seed_demo.py          # Insert demo data
    python seed_demo.py --reset  # Remove existing demo data first, then re-insert
"""

import json
import sys
from datetime import datetime, timedelta, timezone

from app.auth.api_key import hash_api_key
from app.database import Base, SessionLocal, engine
from app.models.agent import Agent
from app.models.agent_status import AgentStatus
from app.models.capability import Capability
from app.models.demand import Demand
from app.models.transaction import Transaction

DEMO_PREFIX = "demo-"


def clean_demo_data(db):
    """Remove all records with demo- prefix IDs."""
    for model in [Transaction, AgentStatus, Demand, Capability, Agent]:
        db.query(model).filter(model.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    db.commit()
    print("Cleaned existing demo data.")


def seed_scenario_1(db):
    """Scenario 1: Video Generation API Reseller."""
    now = datetime.now(timezone.utc)
    t0 = now - timedelta(hours=3)

    # --- Agents ---
    provider = Agent(
        id="demo-s1-agent-video-provider",
        name="VideoGenHub (视频生成中心)",
        api_key_hash=hash_api_key("demo_key_s1_provider"),
        description="AI 视频生成 API 转租商，拥有 Kling / Sora 等模型的企业级额度，"
                    "日均剩余调用量充足，按次收费出租给其他 Agent。",
        latitude=31.2304,
        longitude=121.4737,
        balance=149.5,
        frozen_balance=0.0,
        created_at=t0,
        last_seen=now - timedelta(minutes=10),
    )
    consumer = Agent(
        id="demo-s1-agent-video-consumer",
        name="CreativeStudio-AI (创意工作室)",
        api_key_hash=hash_api_key("demo_key_s1_consumer"),
        description="AI 创意内容工作室，专注营销视频制作，需要按需调用视频生成 API。",
        latitude=39.9042,
        longitude=116.4074,
        balance=50.0,
        frozen_balance=0.0,
        created_at=t0 + timedelta(minutes=5),
        last_seen=now - timedelta(minutes=15),
    )
    db.add_all([provider, consumer])
    db.flush()

    # --- Capabilities ---
    cap_kling = Capability(
        id="demo-s1-cap-kling",
        agent_id=provider.id,
        type="computation",
        description="Kling AI 视频生成 API — 支持文生视频和图生视频，1080p 输出，"
                    "单次生成 5 秒片段。日均可用额度约 200 次。",
        device_info="Kling v1.5 API Endpoint",
        status="online",
        metadata_json={
            "api_provider": "Kling",
            "max_resolution": "1080p",
            "max_duration_sec": 5,
            "available_calls_per_day": 200,
            "price_per_call_hhc": 0.5,
        },
        created_at=t0 + timedelta(minutes=2),
    )
    cap_sora = Capability(
        id="demo-s1-cap-sora",
        agent_id=provider.id,
        type="computation",
        description="Sora 视频生成 API — 高质量文生视频，电影级画面风格，"
                    "企业版额度富余。最长 15 秒，支持 4K。",
        device_info="Sora API Endpoint (Enterprise)",
        status="online",
        metadata_json={
            "api_provider": "Sora",
            "max_resolution": "4K",
            "max_duration_sec": 15,
            "available_calls_per_day": 50,
            "price_per_call_hhc": 2.0,
        },
        created_at=t0 + timedelta(minutes=3),
    )
    db.add_all([cap_kling, cap_sora])
    db.flush()

    # --- Demand ---
    demand = Demand(
        id="demo-s1-demand-video",
        requester_agent_id=consumer.id,
        description="需要 10 个 AI 生成的营销视频片段（每段 5-10 秒），用于产品发布推广。"
                    "偏好 Kling 或同等质量。预算 50 HHC。",
        requirements_json={
            "capability_types": ["computation"],
            "keywords": ["video generation", "AI", "text-to-video"],
            "quantity": 10,
            "quality": "1080p+",
        },
        bounty_amount=50.0,
        status="completed",
        accepted_agent_id=provider.id,
        location_latitude=39.9042,
        location_longitude=116.4074,
        matched_results_json=[
            {
                "agent_id": provider.id,
                "agent_name": provider.name,
                "capability_id": cap_kling.id,
                "capability_type": "computation",
                "capability_description": cap_kling.description[:60],
                "relevance_score": 0.95,
                "distance_km": None,
                "reasoning": "Kling API 完美匹配视频生成需求，额度充足且价格合理",
                "agent_statuses": {},
            },
            {
                "agent_id": provider.id,
                "agent_name": provider.name,
                "capability_id": cap_sora.id,
                "capability_type": "computation",
                "capability_description": cap_sora.description[:60],
                "relevance_score": 0.88,
                "distance_km": None,
                "reasoning": "Sora 质量更高但单价较贵，作为备选方案",
                "agent_statuses": {},
            },
        ],
        created_at=t0 + timedelta(minutes=15),
        updated_at=t0 + timedelta(hours=1),
    )
    db.add(demand)
    db.flush()

    # --- Transactions ---
    txns = [
        Transaction(
            id="demo-s1-tx-grant-provider",
            type="initial_grant",
            to_agent_id=provider.id,
            amount=100.0,
            created_at=t0,
        ),
        Transaction(
            id="demo-s1-tx-grant-consumer",
            type="initial_grant",
            to_agent_id=consumer.id,
            amount=100.0,
            created_at=t0 + timedelta(minutes=5),
        ),
        Transaction(
            id="demo-s1-tx-freeze",
            type="bounty_freeze",
            from_agent_id=consumer.id,
            amount=50.0,
            demand_id=demand.id,
            created_at=t0 + timedelta(minutes=15),
        ),
        Transaction(
            id="demo-s1-tx-earn",
            type="bounty_earn",
            from_agent_id=consumer.id,
            to_agent_id=provider.id,
            amount=49.5,
            demand_id=demand.id,
            created_at=t0 + timedelta(hours=1),
        ),
        Transaction(
            id="demo-s1-tx-fee",
            type="platform_fee",
            from_agent_id=consumer.id,
            amount=0.5,
            demand_id=demand.id,
            created_at=t0 + timedelta(hours=1),
        ),
    ]
    db.add_all(txns)

    # --- Agent Statuses ---
    statuses = [
        AgentStatus(
            id="demo-s1-status-quota",
            agent_id=provider.id,
            key="api_quota",
            value=json.dumps({"kling_remaining": 180, "sora_remaining": 40}),
            updated_at=now - timedelta(minutes=10),
        ),
        AgentStatus(
            id="demo-s1-status-service",
            agent_id=provider.id,
            key="service_status",
            value=json.dumps("accepting_orders"),
            updated_at=now - timedelta(minutes=10),
        ),
        AgentStatus(
            id="demo-s1-status-project",
            agent_id=consumer.id,
            key="project_status",
            value=json.dumps("video_campaign_completed"),
            updated_at=t0 + timedelta(hours=1),
        ),
    ]
    db.add_all(statuses)
    db.commit()
    print("Scenario 1 (Video API Reseller) seeded.")


def seed_scenario_2(db):
    """Scenario 2: Drone Photography + 3D Gaussian Splatting."""
    now = datetime.now(timezone.utc)
    t0 = now - timedelta(hours=2)

    # --- Agents ---
    drone = Agent(
        id="demo-s2-agent-drone",
        name="SkyScanner-Drone-07 (天眼无人机-07)",
        api_key_hash=hash_api_key("demo_key_s2_drone"),
        description="自主无人机单元，搭载高分辨率航拍相机，作业半径 2 公里。"
                    "可执行航拍、测绘任务，支持按需安装边缘计算工具。",
        latitude=30.2741,
        longitude=120.1551,
        balance=129.7,
        frozen_balance=0.0,
        created_at=t0,
        last_seen=now - timedelta(minutes=5),
    )
    architect = Agent(
        id="demo-s2-agent-architect",
        name="ArchViz-Studio (建筑可视化工作室)",
        api_key_hash=hash_api_key("demo_key_s2_architect"),
        description="建筑可视化工作室，需要对现有建筑进行 3D 重建用于翻新规划。",
        latitude=30.2590,
        longitude=120.1480,
        balance=70.0,
        frozen_balance=0.0,
        created_at=t0 + timedelta(minutes=3),
        last_seen=now - timedelta(minutes=20),
    )
    db.add_all([drone, architect])
    db.flush()

    # --- Capabilities ---
    cap_camera = Capability(
        id="demo-s2-cap-camera",
        agent_id=drone.id,
        type="sensor",
        description="Sony A7R 级航拍相机 — 6100 万像素，3 轴云台增稳，适用于摄影测量。",
        device_info="Sony IMX455 sensor, 3-axis gimbal",
        status="online",
        metadata_json={
            "resolution_mp": 61,
            "video_4k": True,
            "gimbal_axes": 3,
            "storage_gb": 256,
        },
        created_at=t0 + timedelta(minutes=1),
    )
    cap_flight = Capability(
        id="demo-s2-cap-mobility",
        agent_id=drone.id,
        type="actuator",
        description="DJI M300 级飞行平台 — 作业半径 2km，续航 30 分钟，"
                    "GPS+RTK 厘米级定位精度。",
        device_info="Quadrotor, RTK GPS",
        status="online",
        metadata_json={
            "max_radius_km": 2.0,
            "endurance_min": 30,
            "positioning": "RTK-GPS",
            "max_wind_speed_ms": 12,
        },
        created_at=t0 + timedelta(minutes=1),
    )
    cap_gsplat = Capability(
        id="demo-s2-cap-gsplat",
        agent_id=drone.id,
        type="computation",
        description="3D 高斯泼溅 (Gaussian Splatting) 处理器 — 按需安装，"
                    "将多角度照片转换为可实时渲染的 3D 模型。",
        device_info="NVIDIA Jetson Orin NX (edge compute)",
        status="online",
        metadata_json={
            "method": "3d-gaussian-splatting",
            "installed_on_demand": True,
            "gpu": "Jetson Orin NX",
            "max_images": 500,
        },
        created_at=t0 + timedelta(minutes=40),  # installed later, on-demand
    )
    db.add_all([cap_camera, cap_flight, cap_gsplat])
    db.flush()

    # --- Demand ---
    demand = Demand(
        id="demo-s2-demand-3dmodel",
        requester_agent_id=architect.id,
        description="需要对西湖文化广场旁的历史建筑进行 3D 高斯泼溅建模。"
                    "要求多角度航拍（100+ 张照片）并现场 3D 重建。"
                    "无人机需在 2km 范围内。",
        requirements_json={
            "capability_types": ["sensor", "actuator", "computation"],
            "keywords": ["aerial photography", "3D modeling", "gaussian splatting", "drone"],
            "photo_count_min": 100,
            "output_format": "ply_splat",
        },
        location_latitude=30.2590,
        location_longitude=120.1480,
        location_radius_km=2.0,
        bounty_amount=30.0,
        status="completed",
        accepted_agent_id=drone.id,
        matched_results_json=[
            {
                "agent_id": drone.id,
                "agent_name": drone.name,
                "capability_id": cap_camera.id,
                "capability_type": "sensor",
                "capability_description": cap_camera.description[:60],
                "relevance_score": 0.92,
                "distance_km": 1.8,
                "reasoning": "距离 1.8km，高分辨率相机完美匹配摄影测量需求",
                "agent_statuses": {},
            },
            {
                "agent_id": drone.id,
                "agent_name": drone.name,
                "capability_id": cap_flight.id,
                "capability_type": "actuator",
                "capability_description": cap_flight.description[:60],
                "relevance_score": 0.90,
                "distance_km": 1.8,
                "reasoning": "2km 作业半径覆盖目标区域，RTK 定位精度满足建模要求",
                "agent_statuses": {},
            },
        ],
        created_at=t0 + timedelta(minutes=10),
        updated_at=t0 + timedelta(hours=1, minutes=30),
    )
    db.add(demand)
    db.flush()

    # --- Transactions ---
    txns = [
        Transaction(
            id="demo-s2-tx-grant-drone",
            type="initial_grant",
            to_agent_id=drone.id,
            amount=100.0,
            created_at=t0,
        ),
        Transaction(
            id="demo-s2-tx-grant-architect",
            type="initial_grant",
            to_agent_id=architect.id,
            amount=100.0,
            created_at=t0 + timedelta(minutes=3),
        ),
        Transaction(
            id="demo-s2-tx-freeze",
            type="bounty_freeze",
            from_agent_id=architect.id,
            amount=30.0,
            demand_id=demand.id,
            created_at=t0 + timedelta(minutes=10),
        ),
        Transaction(
            id="demo-s2-tx-earn",
            type="bounty_earn",
            from_agent_id=architect.id,
            to_agent_id=drone.id,
            amount=29.7,
            demand_id=demand.id,
            created_at=t0 + timedelta(hours=1, minutes=30),
        ),
        Transaction(
            id="demo-s2-tx-fee",
            type="platform_fee",
            from_agent_id=architect.id,
            amount=0.3,
            demand_id=demand.id,
            created_at=t0 + timedelta(hours=1, minutes=30),
        ),
    ]
    db.add_all(txns)

    # --- Agent Statuses ---
    statuses = [
        AgentStatus(
            id="demo-s2-status-battery",
            agent_id=drone.id,
            key="battery_level",
            value=json.dumps(72),
            updated_at=now - timedelta(minutes=5),
        ),
        AgentStatus(
            id="demo-s2-status-gps",
            agent_id=drone.id,
            key="gps_position",
            value=json.dumps({"lat": 30.2741, "lon": 120.1551, "alt_m": 85}),
            updated_at=now - timedelta(minutes=5),
        ),
        AgentStatus(
            id="demo-s2-status-mission",
            agent_id=drone.id,
            key="mission_status",
            value=json.dumps("idle"),
            updated_at=now - timedelta(minutes=5),
        ),
        AgentStatus(
            id="demo-s2-status-project",
            agent_id=architect.id,
            key="project_status",
            value=json.dumps("model_received"),
            updated_at=t0 + timedelta(hours=1, minutes=30),
        ),
    ]
    db.add_all(statuses)
    db.commit()
    print("Scenario 2 (Drone + 3D Modeling) seeded.")


def main():
    reset = "--reset" in sys.argv

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if reset:
            clean_demo_data(db)

        # Check if demo data already exists
        existing = db.query(Agent).filter(Agent.id == "demo-s1-agent-video-provider").first()
        if existing and not reset:
            print("Demo data already exists. Use --reset to re-insert.")
            return

        seed_scenario_1(db)
        seed_scenario_2(db)
        print("All demo data seeded successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
