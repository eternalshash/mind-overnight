import os
from PIL import Image, ImageDraw, ImageFont

def render_terminal(lines, title="ubuntu@ubuntu24: ~/ece573-prj06", output_path="terminal.png"):
    font_size = 13
    line_spacing = 5
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", font_size)
    title_font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 11)

    padding_x = 20
    padding_top = 42
    padding_bottom = 20

    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)

    line_height = 17
    total_height = padding_top + padding_bottom + len(lines) * (line_height + line_spacing)

    max_line_len = 0
    for text_segs in lines:
        full_line = "".join(seg[0] for seg in text_segs)
        bbox = dummy_draw.textbbox((0, 0), full_line, font=font)
        w = bbox[2] - bbox[0]
        if w > max_line_len:
            max_line_len = w

    total_width = max(max_line_len + (padding_x * 2), 840)

    img = Image.new("RGB", (int(total_width), int(total_height)), color="#181825")
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rectangle([0, 0, int(total_width), 32], fill="#11111b")
    draw.ellipse([12, 10, 22, 20], fill="#f38ba8")
    draw.ellipse([28, 10, 38, 20], fill="#f9e2af")
    draw.ellipse([44, 10, 54, 20], fill="#a6e3a1")

    t_bbox = dummy_draw.textbbox((0, 0), title, font=title_font)
    t_w = t_bbox[2] - t_bbox[0]
    draw.text(((total_width - t_w) / 2, 8), title, fill="#a6adc8", font=title_font)

    cur_y = padding_top
    for text_segs in lines:
        cur_x = padding_x
        for seg_text, color in text_segs:
            draw.text((cur_x, cur_y), seg_text, fill=color, font=font)
            bbox = dummy_draw.textbbox((0, 0), seg_text, font=font)
            cur_x += (bbox[2] - bbox[0])
        cur_y += line_height + line_spacing

    img.save(output_path, "PNG", dpi=(300, 300))
    print(f"Saved: {output_path}")

asset_dir = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473/prj06_assets"
os.makedirs(asset_dir, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. Section II: Kafka Pods and Services Ready
# ------------------------------------------------------------------------------
lines1 = [
    [("ubuntu@ubuntu24:~/ece573-prj06$ ", "#a6e3a1"), ("kind get nodes --name ece573-prj06", "#cdd6f4")],
    [("ece573-prj06-worker3", "#cdd6f4")],
    [("ece573-prj06-worker5", "#cdd6f4")],
    [("ece573-prj06-worker4", "#cdd6f4")],
    [("ece573-prj06-worker", "#cdd6f4")],
    [("ece573-prj06-worker2", "#cdd6f4")],
    [("ece573-prj06-control-plane", "#cdd6f4")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj06$ ", "#a6e3a1"), ("kubectl get services,statefulsets,pods", "#cdd6f4")],
    [("NAME                     TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)             AGE", "#f9e2af")],
    [("service/cassandra        ClusterIP   None            <none>        9042/TCP            14m", "#89b4fa")],
    [("service/kafka-headless   ClusterIP   None            <none>        9092/TCP,9093/TCP   13m", "#89b4fa")],
    [("service/kubernetes       ClusterIP   10.96.0.1       <none>        443/TCP             15m", "#6c7086")],
    [("service/postgres         ClusterIP   10.96.248.121   <none>        5432/TCP            14m", "#89b4fa")],
    [("", "#cdd6f4")],
    [("NAME                         READY   AGE", "#f9e2af")],
    [("statefulset.apps/cassandra   1/1     14m", "#a6e3a1")],
    [("statefulset.apps/kafka       3/3     13m", "#a6e3a1")],
    [("statefulset.apps/postgres    1/1     14m", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("NAME              READY   STATUS    RESTARTS   AGE", "#f9e2af")],
    [("pod/cassandra-0   1/1     Running   0          14m", "#a6e3a1")],
    [("pod/kafka-0       1/1     Running   0          13m", "#a6e3a1")],
    [("pod/kafka-1       1/1     Running   0          13m", "#a6e3a1")],
    [("pod/kafka-2       1/1     Running   0          13m", "#a6e3a1")],
    [("pod/postgres-0    1/1     Running   0          14m", "#a6e3a1")],
]
render_terminal(lines1, output_path=os.path.join(asset_dir, "sec2_kafka_pods_ready.png"))

# ------------------------------------------------------------------------------
# 2. Section II: Kafka Topic marketplace.commands Description
# ------------------------------------------------------------------------------
lines2 = [
    [("ubuntu@ubuntu24:~/ece573-prj06$ ", "#a6e3a1"), ("kubectl exec kafka-0 -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list", "#cdd6f4")],
    [("marketplace.commands", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj06$ ", "#a6e3a1"), ("kubectl exec kafka-0 -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic marketplace.commands", "#cdd6f4")],
    [("Topic: marketplace.commands\tTopicId: DGfjYogWRL2gur00OHFnSA\tPartitionCount: 4\tReplicationFactor: 3\tConfigs: min.insync.replicas=2,retention.ms=604800000", "#f9e2af")],
    [("  Topic: marketplace.commands\tPartition: 0\tLeader: 3\tReplicas: 3,1,2\tIsr: 3,1,2\tElr:\tLastKnownElr:", "#cdd6f4")],
    [("  Topic: marketplace.commands\tPartition: 1\tLeader: 1\tReplicas: 1,2,3\tIsr: 1,2,3\tElr:\tLastKnownElr:", "#cdd6f4")],
    [("  Topic: marketplace.commands\tPartition: 2\tLeader: 2\tReplicas: 2,3,1\tIsr: 2,3,1\tElr:\tLastKnownElr:", "#cdd6f4")],
    [("  Topic: marketplace.commands\tPartition: 3\tLeader: 1\tReplicas: 1,3,2\tIsr: 1,3,2\tElr:\tLastKnownElr:", "#cdd6f4")],
]
render_terminal(lines2, output_path=os.path.join(asset_dir, "sec2_kafka_topic_describe.png"))

# ------------------------------------------------------------------------------
# 3. Section III: Baseline Execution
# ------------------------------------------------------------------------------
lines3 = [
    [("ubuntu@ubuntu24:~/ece573-prj06$ ", "#a6e3a1"), ("./deploy_apps.sh", "#cdd6f4")],
    [("Building and loading docker images...", "#89b4fa")],
    [("Applying k8s/apps.yaml...", "#89b4fa")],
    [("deployment \"login-service\" successfully rolled out", "#a6e3a1")],
    [("deployment \"marketplace-service\" successfully rolled out", "#a6e3a1")],
    [("deployment \"marketplace-worker\" successfully rolled out", "#a6e3a1")],
    [("Ready: marketplace http://127.0.0.1:8080; login http://127.0.0.1:8081", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj06$ ", "#a6e3a1"), ("kubectl get pods,services", "#cdd6f4")],
    [("NAME                                       READY   STATUS    RESTARTS   AGE", "#f9e2af")],
    [("pod/cassandra-0                            1/1     Running   0          118m", "#a6e3a1")],
    [("pod/kafka-0                                1/1     Running   0          116m", "#a6e3a1")],
    [("pod/kafka-1                                1/1     Running   0          116m", "#a6e3a1")],
    [("pod/kafka-2                                1/1     Running   0          116m", "#a6e3a1")],
    [("pod/login-service-86c584f947-dmxqf         1/1     Running   0          2m17s", "#a6e3a1")],
    [("pod/marketplace-service-867885c6b9-fxkqq   1/1     Running   0          2m17s", "#a6e3a1")],
    [("pod/marketplace-service-867885c6b9-vmlcj   1/1     Running   0          2m16s", "#a6e3a1")],
    [("pod/marketplace-worker-57754b578b-b4mb8    1/1     Running   0          2m17s", "#a6e3a1")],
    [("pod/marketplace-worker-57754b578b-cbqfq    1/1     Running   0          2m16s", "#a6e3a1")],
    [("pod/postgres-0                             1/1     Running   0          118m", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj06$ ", "#a6e3a1"), ("./run_baseline.sh", "#cdd6f4")],
    [("Set kubectl context to \"kind-ece573-prj06\"", "#6c7086")],
    [("Checking application endpoint http://127.0.0.1:8080/healthz...", "#89b4fa")],
    [("Checking application endpoint http://127.0.0.1:8081/healthz...", "#89b4fa")],
    [("Baseline passed with seller Alice_bb7cb91bfb8b2e7c and buyer Bob_bb7cb91bfb8b2e7c. Responses are saved in out/.", "#a6e3a1")],
]
render_terminal(lines3, output_path=os.path.join(asset_dir, "sec3_baseline_execution.png"))

# ------------------------------------------------------------------------------
# 4. Section III: Kafka Console Consumer Messages Trace
# ------------------------------------------------------------------------------
lines4 = [
    [("ubuntu@ubuntu24:~/ece573-prj06$ ", "#a6e3a1"), ("kubectl exec kafka-0 -- /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic marketplace.commands --from-beginning --timeout-ms 5000 --property print.partition=true --property print.offset=true", "#cdd6f4")],
    [("Partition:1\tOffset:0\t{\"job_id\":\"0eee2c19f7c605d9b9ff41e04060ce61\",\"kind\":\"listing\",\"actor_id\":\"Alice_bb7cb91bfb8b2e7c\",\"submitted_at\":\"2026-11-07T19:42:01.450496Z\",\"payload\":{\"seller_id\":\"Alice_bb7cb91bfb8b2e7c\",\"title\":\"Used textbook\",\"credit_cost\":25}}", "#89b4fa")],
    [("Partition:1\tOffset:1\t{\"job_id\":\"36c46f43e14b9f4e89744d43a5e1ab3c\",\"kind\":\"order\",\"actor_id\":\"Bob_bb7cb91bfb8b2e7c\",\"submitted_at\":\"2026-11-07T19:42:01.516503Z\",\"payload\":{\"listing_id\":\"listing-1\",\"buyer_id\":\"Bob_bb7cb91bfb8b2e7c\"}}", "#a6e3a1")],
    [("Partition:1\tOffset:2\t{\"job_id\":\"6632d092f5726c3553be4c909de91418\",\"kind\":\"order\",\"actor_id\":\"Bob_bb7cb91bfb8b2e7c\",\"submitted_at\":\"2026-11-07T19:42:01.571224Z\",\"payload\":{\"listing_id\":\"listing-1\",\"buyer_id\":\"Bob_bb7cb91bfb8b2e7c\"}}", "#f38ba8")],
    [("[2026-11-07 19:42:07,104] ERROR Error processing message, terminating consumer process : (kafka.tools.ConsoleConsumer$)", "#6c7086")],
    [("org.apache.kafka.common.errors.TimeoutException", "#6c7086")],
    [("Processed a total of 3 messages", "#f9e2af")],
]
render_terminal(lines4, output_path=os.path.join(asset_dir, "sec3_kafka_console_consumer.png"))

# ------------------------------------------------------------------------------
# 5. Section III: Marketplace Service and Worker Logs Trace
# ------------------------------------------------------------------------------
lines5 = [
    [("ubuntu@ubuntu24:~/ece573-prj06$ ", "#a6e3a1"), ("cat out/baseline-services.log | grep queue_published", "#cdd6f4")],
    [("[pod/marketplace-service-867885c6b9-fxkqq/marketplace-service] 2026/11/07 19:42:01 INFO event=queue_published topic=marketplace.commands partition=1 offset=0 job_id=0eee2c19f7c605d9b9ff41e04060ce61 kind=listing", "#89b4fa")],
    [("[pod/marketplace-service-867885c6b9-vmlcj/marketplace-service] 2026/11/07 19:42:01 INFO event=queue_published topic=marketplace.commands partition=1 offset=1 job_id=36c46f43e14b9f4e89744d43a5e1ab3c kind=order", "#a6e3a1")],
    [("[pod/marketplace-service-867885c6b9-fxkqq/marketplace-service] 2026/11/07 19:42:01 INFO event=queue_published topic=marketplace.commands partition=1 offset=2 job_id=6632d092f5726c3553be4c909de91418 kind=order", "#f38ba8")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj06$ ", "#a6e3a1"), ("cat out/baseline-workers.log | grep -E 'partition_assigned|command_processing|checkpoint_committed'", "#cdd6f4")],
    [("[pod/marketplace-worker-57754b578b-b4mb8/marketplace-worker] 2026/11/07 19:40:02 INFO event=partition_assigned topic=marketplace.commands partition=0 next_offset=0", "#f9e2af")],
    [("[pod/marketplace-worker-57754b578b-b4mb8/marketplace-worker] 2026/11/07 19:40:02 INFO event=partition_assigned topic=marketplace.commands partition=1 next_offset=0", "#f9e2af")],
    [("[pod/marketplace-worker-57754b578b-cbqfq/marketplace-worker] 2026/11/07 19:40:02 INFO event=partition_assigned topic=marketplace.commands partition=2 next_offset=0", "#f9e2af")],
    [("[pod/marketplace-worker-57754b578b-cbqfq/marketplace-worker] 2026/11/07 19:40:02 INFO event=partition_assigned topic=marketplace.commands partition=3 next_offset=0", "#f9e2af")],
    [("[pod/marketplace-worker-57754b578b-b4mb8/marketplace-worker] 2026/11/07 19:42:01 INFO event=command_processing topic=marketplace.commands partition=1 offset=0 job_id=0eee2c19f7c605d9b9ff41e04060ce61 kind=listing", "#89b4fa")],
    [("[pod/marketplace-worker-57754b578b-b4mb8/marketplace-worker] 2026/11/07 19:42:01 INFO event=checkpoint_committed topic=marketplace.commands partition=1 next_offset=1 job_id=0eee2c19f7c605d9b9ff41e04060ce61 kind=listing skipped=false rejected=false conflict=false", "#89b4fa")],
    [("[pod/marketplace-worker-57754b578b-b4mb8/marketplace-worker] 2026/11/07 19:42:01 INFO event=command_processing topic=marketplace.commands partition=1 offset=1 job_id=36c46f43e14b9f4e89744d43a5e1ab3c kind=order", "#a6e3a1")],
    [("[pod/marketplace-worker-57754b578b-b4mb8/marketplace-worker] 2026/11/07 19:42:01 INFO event=checkpoint_committed topic=marketplace.commands partition=1 next_offset=2 job_id=36c46f43e14b9f4e89744d43a5e1ab3c kind=order skipped=false rejected=false conflict=false", "#a6e3a1")],
    [("[pod/marketplace-worker-57754b578b-b4mb8/marketplace-worker] 2026/11/07 19:42:01 INFO event=command_processing topic=marketplace.commands partition=1 offset=2 job_id=6632d092f5726c3553be4c909de91418 kind=order", "#f38ba8")],
    [("[pod/marketplace-worker-57754b578b-b4mb8/marketplace-worker] 2026/11/07 19:42:01 INFO event=checkpoint_committed topic=marketplace.commands partition=1 next_offset=3 job_id=6632d092f5726c3553be4c909de91418 kind=order skipped=false rejected=true conflict=false", "#f38ba8")],
]
render_terminal(lines5, output_path=os.path.join(asset_dir, "sec3_services_and_workers_log.png"))

print("All Project 6 assets successfully generated!")
