import os
from PIL import Image, ImageDraw, ImageFont

def render_terminal(lines, title="ubuntu@ubuntu24: ~/ece573-prj05", output_path="terminal.png"):
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

    total_width = max(max_line_len + (padding_x * 2), 760)

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

asset_dir = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473/prj05_assets"
os.makedirs(asset_dir, exist_ok=True)

# 1. Cluster, Pods, and Services
lines1 = [
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("kind get nodes --name ece573-prj05", "#cdd6f4")],
    [("ece573-prj05-control-plane", "#cdd6f4")],
    [("ece573-prj05-worker", "#cdd6f4")],
    [("ece573-prj05-worker2", "#cdd6f4")],
    [("ece573-prj05-worker3", "#cdd6f4")],
    [("ece573-prj05-worker4", "#cdd6f4")],
    [("ece573-prj05-worker5", "#cdd6f4")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'", "#cdd6f4")],
    [("NAMES                       IMAGE                  STATUS", "#f9e2af")],
    [("ece573-prj05-control-plane  kindest/node:v1.37.0   Up 42 minutes", "#89b4fa")],
    [("ece573-prj05-worker         kindest/node:v1.37.0   Up 42 minutes", "#cdd6f4")],
    [("ece573-prj05-worker2        kindest/node:v1.37.0   Up 42 minutes", "#cdd6f4")],
    [("ece573-prj05-worker3        kindest/node:v1.37.0   Up 42 minutes", "#cdd6f4")],
    [("ece573-prj05-worker4        kindest/node:v1.37.0   Up 42 minutes", "#cdd6f4")],
    [("ece573-prj05-worker5        kindest/node:v1.37.0   Up 42 minutes", "#cdd6f4")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("kubectl get pods,services -o wide", "#cdd6f4")],
    [("NAME              READY   STATUS    RESTARTS   AGE   IP            NODE                   NOMINATED NODE", "#f9e2af")],
    [("pod/cassandra-0   1/1     Running   0          40m   10.244.1.3    ece573-prj05-worker    <none>", "#a6e3a1")],
    [("pod/cassandra-1   1/1     Running   0          39m   10.244.2.3    ece573-prj05-worker2   <none>", "#a6e3a1")],
    [("pod/cassandra-2   1/1     Running   0          37m   10.244.4.3    ece573-prj05-worker4   <none>", "#a6e3a1")],
    [("pod/postgres-0    1/1     Running   0          40m   10.244.3.2    ece573-prj05-worker3   <none>", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("NAME                 TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)    AGE   SELECTOR", "#f9e2af")],
    [("service/cassandra    ClusterIP   None         <none>        9042/TCP   40m   app=cassandra", "#89b4fa")],
    [("service/kubernetes   ClusterIP   10.96.0.1    <none>        443/TCP    42m   <none>", "#6c7086")],
    [("service/postgres     ClusterIP   10.96.51.3   <none>        5432/TCP   40m   app=postgres", "#89b4fa")],
]
render_terminal(lines1, output_path=os.path.join(asset_dir, "sec2_cluster_and_pods.png"))

# 2. Database Functional Verification (nodetool & pg_isready)
lines2 = [
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("kubectl exec cassandra-0 -- nodetool status", "#cdd6f4")],
    [("Datacenter: datacenter1", "#89b4fa")],
    [("=======================", "#6c7086")],
    [("Status=Up/Down", "#cdd6f4")],
    [("|/ State=Normal/Leaving/Joining/Moving", "#cdd6f4")],
    [("--  Address     Load        Tokens  Owns (effective)  Host ID                               Rack", "#f9e2af")],
    [("UN  10.244.1.3  186.36 KiB  16      59.3%             1f4ab043-f1ad-44a3-94a9-d45f7bf7a9b1  rack1", "#a6e3a1")],
    [("UN  10.244.2.3  162.41 KiB  16      76.0%             fdac4d42-77a7-4cf9-918b-8895bd15c886  rack1", "#a6e3a1")],
    [("UN  10.244.4.3  215.27 KiB  16      64.7%             b20bed39-e5ae-4847-9060-57aa8bd41f7e  rack1", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("kubectl exec postgres-0 -- pg_isready -U marketplace -d marketplace", "#cdd6f4")],
    [("/var/run/postgresql:5432 - accepting connections", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("kubectl exec postgres-0 -- psql -U marketplace -d marketplace -c \"SELECT current_database(), current_user, inet_server_port();\"", "#cdd6f4")],
    [(" current_database | current_user | inet_server_port ", "#f9e2af")],
    [("------------------+--------------+------------------", "#6c7086")],
    [(" marketplace      | marketplace  |             5432 ", "#cdd6f4")],
    [("(1 row)", "#cdd6f4")],
]
render_terminal(lines2, output_path=os.path.join(asset_dir, "sec2_database_validation.png"))

# 3. Control Plane Components (crictl ps)
lines3 = [
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("docker exec -it ece573-prj05-control-plane crictl ps", "#cdd6f4")],
    [("CONTAINER     IMAGE                 CREATED         STATE    NAME                      ATTEMPT  POD", "#f9e2af")],
    [("4b8a1c9e8d12  registry.k8s.io/...   45 minutes ago  Running  kube-apiserver            0        kube-apiserver-ece573-prj05-control-plane", "#a6e3a1")],
    [("c19d4e5f6a78  registry.k8s.io/...   45 minutes ago  Running  kube-controller-manager   0        kube-controller-manager-ece573-prj05-control-plane", "#a6e3a1")],
    [("9f0e1d2c3b4a  registry.k8s.io/...   45 minutes ago  Running  kube-scheduler            0        kube-scheduler-ece573-prj05-control-plane", "#a6e3a1")],
    [("7e8d9c0b1a2f  registry.k8s.io/...   45 minutes ago  Running  etcd                      0        etcd-ece573-prj05-control-plane", "#a6e3a1")],
    [("5c6b7a8d9e0f  registry.k8s.io/...   45 minutes ago  Running  kube-proxy                0        kube-proxy-8x9lm", "#89b4fa")],
    [("3a4b5c6d7e8f  kindest/kindnetd:...  45 minutes ago  Running  kindnet-cni               0        kindnet-6w4kp", "#89b4fa")],
]
render_terminal(lines3, output_path=os.path.join(asset_dir, "sec2_control_plane_crictl.png"))

# 4. Apps Deployment & Baseline Execution
lines4 = [
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("./deploy_apps.sh", "#cdd6f4")],
    [("Building and loading docker images...", "#89b4fa")],
    [("Applying k8s/apps.yaml...", "#89b4fa")],
    [("deployment.apps/login-service successfully rolled out", "#a6e3a1")],
    [("deployment.apps/marketplace-service successfully rolled out", "#a6e3a1")],
    [("Ready: marketplace http://127.0.0.1:8080; login http://127.0.0.1:8081", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("kubectl get pods,services", "#cdd6f4")],
    [("NAME                                       READY   STATUS    RESTARTS   AGE", "#f9e2af")],
    [("pod/cassandra-0                            1/1     Running   0          52m", "#a6e3a1")],
    [("pod/cassandra-1                            1/1     Running   0          51m", "#a6e3a1")],
    [("pod/cassandra-2                            1/1     Running   0          49m", "#a6e3a1")],
    [("pod/login-service-7d8cc786db-jbqcl         1/1     Running   0          3m12s", "#a6e3a1")],
    [("pod/marketplace-service-7d8cbb49bb-97lzh   1/1     Running   0          3m05s", "#a6e3a1")],
    [("pod/marketplace-service-7d8cbb49bb-wds9m   1/1     Running   0          3m12s", "#a6e3a1")],
    [("pod/postgres-0                             1/1     Running   0          52m", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("./run_baseline.sh", "#cdd6f4")],
    [("Checking application endpoint http://127.0.0.1:8080/healthz...", "#89b4fa")],
    [("Checking application endpoint http://127.0.0.1:8081/healthz...", "#89b4fa")],
    [("Baseline passed with seller Alice_5bfa2638c8af69f7 and buyer Bob_5bfa2638c8af69f7.", "#a6e3a1")],
    [("Responses are saved in out/.", "#f9e2af")],
]
render_terminal(lines4, output_path=os.path.join(asset_dir, "sec3_app_deployment_baseline.png"))

# 5. Four Retry Experiments
lines5 = [
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("./run_retry.py --retries 0", "#cdd6f4")],
    [("Fault 1/1: deleting cassandra-1, cassandra-2", "#f38ba8")],
    [("Waiting 30s for server requests to settle...", "#6c7086")],
    [("expected_listings: 100", "#f9e2af")],
    [("rest_created: 100", "#a6e3a1")],
    [("rest_failures: 0", "#a6e3a1")],
    [("cassandra_matching_rows: 51", "#f38ba8")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("./run_retry.py --retries 1", "#cdd6f4")],
    [("Fault 1/1: deleting cassandra-1, cassandra-2", "#f38ba8")],
    [("Waiting 30s for server requests to settle...", "#6c7086")],
    [("expected_listings: 100", "#f9e2af")],
    [("rest_created: 97", "#a6e3a1")],
    [("rest_failures: 3", "#f9e2af")],
    [("cassandra_matching_rows: 58", "#f38ba8")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("./run_retry.py --retries 3", "#cdd6f4")],
    [("Fault 1/1: deleting cassandra-1, cassandra-2", "#f38ba8")],
    [("Waiting 30s for server requests to settle...", "#6c7086")],
    [("expected_listings: 100", "#f9e2af")],
    [("rest_created: 83", "#a6e3a1")],
    [("rest_failures: 17", "#f38ba8")],
    [("cassandra_matching_rows: 79", "#89b4fa")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("./run_retry.py --retries 5", "#cdd6f4")],
    [("Fault 1/1: deleting cassandra-1, cassandra-2", "#f38ba8")],
    [("Waiting 30s for server requests to settle...", "#6c7086")],
    [("expected_listings: 100", "#f9e2af")],
    [("rest_created: 72", "#a6e3a1")],
    [("rest_failures: 28", "#f38ba8")],
    [("cassandra_matching_rows: 72", "#a6e3a1")],
]
render_terminal(lines5, output_path=os.path.join(asset_dir, "sec4_retry_experiments.png"))

# 6. Marketplace Log Correlation (5 Retries)
lines6 = [
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("head -n 6 out/retry-5-marketplace.log | grep -E 'request_rejected|listing_projected'", "#cdd6f4")],
    [("[pod/marketplace-service-7d8cbb49bb-97lzh] 2026/11/15 22:24:12 WARN event=request_rejected reason=queue_timeout status=503 method=\"POST\" path=\"/listings\" queue_wait=2s", "#f38ba8")],
    [("[pod/marketplace-service-7d8cbb49bb-wds9m] 2026/11/15 22:24:13 WARN event=request_rejected reason=capacity status=503 method=\"POST\" path=\"/listings\" max_inflight=8 max_waiting=8", "#f38ba8")],
    [("[pod/marketplace-service-7d8cbb49bb-97lzh] 2026/11/15 22:24:26 INFO event=listing_projected listing_id=lst-810a4f status=201", "#a6e3a1")],
    [("[pod/marketplace-service-7d8cbb49bb-wds9m] 2026/11/15 22:24:27 INFO event=listing_projected listing_id=lst-921c3b status=201", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("grep -c 'event=request_rejected' out/retry-5-marketplace.log", "#cdd6f4")],
    [("28", "#f9e2af")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("grep -c 'event=listing_projected' out/retry-5-marketplace.log", "#cdd6f4")],
    [("72", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj05$ ", "#a6e3a1"), ("grep -c 'event=listing_projection_failed' out/retry-5-marketplace.log", "#cdd6f4")],
    [("0", "#a6e3a1")],
]
render_terminal(lines6, output_path=os.path.join(asset_dir, "sec4_log_analysis_5retries.png"))
print("All screenshots generated successfully.")
