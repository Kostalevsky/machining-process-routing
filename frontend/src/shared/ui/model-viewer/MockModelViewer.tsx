import {
    PointerEvent,
    WheelEvent,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";
import styles from "./MockModelViewer.module.scss";

type MockModelViewerProps = {
    fileName: string;
    modelUrl?: string;
    mode?: "card" | "modal";
    onExpand?: () => void;
};

type RotationState = {
    x: number;
    y: number;
    z: number;
    scale: number;
};

const initialRotation: RotationState = {
    x: -24,
    y: 28,
    z: -8,
    scale: 1,
};

type MeshData = {
    vertices: Array<[number, number, number]>;
    edges: Array<[number, number]>;
};

function truncateFileName(name: string, maxLength = 30) {
    if (name.length <= maxLength) {
        return name;
    }

    const dotIndex = name.lastIndexOf(".");
    const extension = dotIndex > 0 ? name.slice(dotIndex) : "";
    const base = extension ? name.slice(0, dotIndex) : name;
    const head = base.slice(0, 14);
    const tail = base.slice(-6);
    return `${head}...${tail}${extension}`;
}

function rotatePoint(
    [x, y, z]: [number, number, number],
    rotation: RotationState,
) {
    const rx = (rotation.x * Math.PI) / 180;
    const ry = (rotation.y * Math.PI) / 180;
    const rz = (rotation.z * Math.PI) / 180;

    let px = x;
    let py = y;
    let pz = z;

    const cosX = Math.cos(rx);
    const sinX = Math.sin(rx);
    [py, pz] = [py * cosX - pz * sinX, py * sinX + pz * cosX];

    const cosY = Math.cos(ry);
    const sinY = Math.sin(ry);
    [px, pz] = [px * cosY + pz * sinY, -px * sinY + pz * cosY];

    const cosZ = Math.cos(rz);
    const sinZ = Math.sin(rz);
    [px, py] = [px * cosZ - py * sinZ, px * sinZ + py * cosZ];

    return [px, py, pz] as const;
}

function parseObj(text: string): MeshData | null {
    const vertices: Array<[number, number, number]> = [];
    const edges = new Set<string>();

    for (const rawLine of text.split("\n")) {
        const line = rawLine.trim();

        if (line.startsWith("v ")) {
            const [, xs, ys, zs] = line.split(/\s+/);
            const x = Number(xs);
            const y = Number(ys);
            const z = Number(zs);

            if ([x, y, z].every((value) => Number.isFinite(value))) {
                vertices.push([x, y, z]);
            }
        }

        if (line.startsWith("f ")) {
            const faceIndices = line
                .split(/\s+/)
                .slice(1)
                .map((part) => Number(part.split("/")[0]) - 1)
                .filter((index) => Number.isInteger(index) && index >= 0);

            for (let index = 0; index < faceIndices.length; index += 1) {
                const a = faceIndices[index];
                const b = faceIndices[(index + 1) % faceIndices.length];
                const edge = a < b ? `${a}-${b}` : `${b}-${a}`;
                edges.add(edge);
            }
        }
    }

    if (vertices.length === 0 || edges.size === 0) {
        return null;
    }

    const xs = vertices.map(([x]) => x);
    const ys = vertices.map(([, y]) => y);
    const zs = vertices.map(([, , z]) => z);
    const center: [number, number, number] = [
        (Math.min(...xs) + Math.max(...xs)) / 2,
        (Math.min(...ys) + Math.max(...ys)) / 2,
        (Math.min(...zs) + Math.max(...zs)) / 2,
    ];

    const centeredVertices = vertices.map(
        ([x, y, z]) =>
            [x - center[0], y - center[1], z - center[2]] as [
                number,
                number,
                number,
            ],
    );
    const radius = Math.max(
        ...centeredVertices.map(([x, y, z]) =>
            Math.sqrt(x * x + y * y + z * z),
        ),
        1,
    );

    return {
        vertices: centeredVertices.map(([x, y, z]) => [
            x / radius,
            y / radius,
            z / radius,
        ]),
        edges: Array.from(edges).map(
            (edge) => edge.split("-").map(Number) as [number, number],
        ),
    };
}

export function MockModelViewer({
    fileName,
    modelUrl,
    mode = "card",
    onExpand,
}: MockModelViewerProps) {
    const [rotation, setRotation] = useState(initialRotation);
    const dragRef = useRef<{ x: number; y: number } | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const [mesh, setMesh] = useState<MeshData | null>(null);
    const isModal = mode === "modal";

    const transform = useMemo(
        () =>
            `translateZ(0) rotateX(${rotation.x}deg) rotateY(${rotation.y}deg) rotateZ(${rotation.z}deg) scale(${rotation.scale})`,
        [rotation],
    );

    useEffect(() => {
        let cancelled = false;

        async function loadMesh() {
            if (!modelUrl || !fileName.toLowerCase().endsWith(".obj")) {
                setMesh(null);
                return;
            }

            try {
                const response = await fetch(modelUrl);
                const text = await response.text();
                const parsed = parseObj(text);

                if (!cancelled) {
                    setMesh(parsed);
                    setRotation(initialRotation);
                }
            } catch {
                if (!cancelled) {
                    setMesh(null);
                }
            }
        }

        loadMesh();

        return () => {
            cancelled = true;
        };
    }, [fileName, modelUrl]);

    useEffect(() => {
        const canvas = canvasRef.current;

        if (!canvas || !mesh) {
            return;
        }

        const context = canvas.getContext("2d");

        if (!context) {
            return;
        }

        function draw() {
            const rect = canvas.getBoundingClientRect();
            const width = Math.max(1, Math.floor(rect.width));
            const height = Math.max(1, Math.floor(rect.height));

            if (canvas.width !== width || canvas.height !== height) {
                canvas.width = width;
                canvas.height = height;
            }

            context.clearRect(0, 0, width, height);
            context.lineJoin = "round";
            context.lineCap = "round";

            const projected = mesh.vertices.map((vertex) => {
                const [x, y, z] = rotatePoint(vertex, rotation);
                const depth = 3.2 + z;
                const perspective = 1 / depth;
                const scale = Math.min(width, height) * 0.34 * rotation.scale;

                return {
                    x: width / 2 + x * scale * perspective,
                    y: height / 2 - y * scale * perspective,
                };
            });

            context.beginPath();
            mesh.edges.forEach(([a, b]) => {
                const start = projected[a];
                const end = projected[b];

                if (!start || !end) {
                    return;
                }

                context.moveTo(start.x, start.y);
                context.lineTo(end.x, end.y);
            });
            context.strokeStyle = "rgba(185, 185, 185, 0.95)";
            context.lineWidth = isModal ? 5 : 4;
            context.stroke();

            context.beginPath();
            mesh.edges.forEach(([a, b]) => {
                const start = projected[a];
                const end = projected[b];

                if (!start || !end) {
                    return;
                }

                context.moveTo(start.x, start.y);
                context.lineTo(end.x, end.y);
            });
            context.strokeStyle = "rgba(112, 112, 112, 0.92)";
            context.lineWidth = isModal ? 1.9 : 1.5;
            context.stroke();
        }

        draw();
        window.addEventListener("resize", draw);
        return () => window.removeEventListener("resize", draw);
    }, [isModal, mesh, rotation]);

    function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
        if ((event.target as HTMLElement).closest("button")) {
            return;
        }

        dragRef.current = { x: event.clientX, y: event.clientY };
        event.currentTarget.setPointerCapture(event.pointerId);
    }

    function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
        if (!dragRef.current) {
            return;
        }

        const dx = event.clientX - dragRef.current.x;
        const dy = event.clientY - dragRef.current.y;

        dragRef.current = { x: event.clientX, y: event.clientY };

        setRotation((current) => ({
            ...current,
            x: current.x - dy * 0.35,
            y: current.y + dx * 0.35,
        }));
    }

    function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
        dragRef.current = null;
        event.currentTarget.releasePointerCapture(event.pointerId);
    }

    function handleWheel(event: WheelEvent<HTMLDivElement>) {
        event.preventDefault();
        setRotation((current) => ({
            ...current,
            scale: Math.min(
                2.4,
                Math.max(0.55, current.scale - event.deltaY * 0.0012),
            ),
        }));
    }

    function updateZoom(nextScale: number) {
        setRotation((current) => ({
            ...current,
            scale: Math.min(2.4, Math.max(0.55, nextScale)),
        }));
    }

    function rotateZ(delta: number) {
        setRotation((current) => ({
            ...current,
            z: current.z + delta,
        }));
    }

    function resetView() {
        setRotation(initialRotation);
    }

    return (
        <div className={isModal ? styles.viewerModal : styles.viewerCard}>
            <div
                className={styles.viewport}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                onPointerCancel={handlePointerUp}
                onWheel={handleWheel}
            >
                {mesh ? (
                    <div className={styles.sceneReal}>
                        <div className={styles.grid} />
                        <canvas ref={canvasRef} className={styles.canvas} />
                    </div>
                ) : (
                    <div className={styles.scene}>
                        <div className={styles.grid} />
                        <div className={styles.modelShadow} />

                        <div className={styles.model} style={{ transform }}>
                            <div className={`${styles.face} ${styles.front}`} />
                            <div className={`${styles.face} ${styles.back}`} />
                            <div className={`${styles.face} ${styles.left}`} />
                            <div className={`${styles.face} ${styles.right}`} />
                            <div className={`${styles.face} ${styles.top}`} />
                            <div
                                className={`${styles.face} ${styles.bottom}`}
                            />
                            <div className={styles.ring} />
                            <div className={styles.core} />
                        </div>
                    </div>
                )}
                {!isModal && onExpand ? (
                    <button
                        type="button"
                        className={styles.expandButton}
                        onPointerDown={(event) => {
                            event.stopPropagation();
                        }}
                        onClick={(event) => {
                            event.stopPropagation();
                            onExpand();
                        }}
                    >
                        Открыть 3D-сцену
                    </button>
                ) : null}
            </div>

            <div className={styles.controls}>
                <button
                    type="button"
                    className={styles.controlButton}
                    onClick={() => updateZoom(rotation.scale + 0.15)}
                >
                    +
                </button>
                <button
                    type="button"
                    className={styles.controlButton}
                    onClick={() => updateZoom(rotation.scale - 0.15)}
                >
                    -
                </button>
                <button
                    type="button"
                    className={styles.controlButtonWide}
                    onClick={resetView}
                >
                    Сбросить вид
                </button>
            </div>
        </div>
    );
}
