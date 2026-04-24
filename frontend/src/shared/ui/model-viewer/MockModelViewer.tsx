import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import styles from "./MockModelViewer.module.scss";

type MockModelViewerProps = {
    fileName: string;
    modelUrl?: string;
    mode?: "card" | "modal";
    onExpand?: () => void;
};

type ViewerScene = {
    camera: THREE.PerspectiveCamera;
    controls: OrbitControls;
    renderer: THREE.WebGLRenderer;
    initialCameraPosition: THREE.Vector3;
    initialTarget: THREE.Vector3;
    object: THREE.Object3D;
};

const modelMaterial = new THREE.MeshStandardMaterial({
    color: 0xc9cccb,
    metalness: 0.08,
    roughness: 0.48,
    side: THREE.DoubleSide,
});

const edgeMaterial = new THREE.LineBasicMaterial({
    color: 0x8c9090,
    transparent: true,
    opacity: 0.58,
});

function disposeObject(object: THREE.Object3D) {
    object.traverse((child) => {
        const mesh = child as THREE.Mesh;

        if (mesh.geometry) {
            mesh.geometry.dispose();
        }
    });
}

function decorateModel(object: THREE.Object3D) {
    object.traverse((child) => {
        const mesh = child as THREE.Mesh;

        if (!mesh.isMesh) {
            return;
        }

        mesh.material = modelMaterial;
        mesh.castShadow = true;
        mesh.receiveShadow = true;

        const edges = new THREE.EdgesGeometry(mesh.geometry, 24);
        const outline = new THREE.LineSegments(edges, edgeMaterial);
        outline.renderOrder = 1;
        mesh.add(outline);
    });
}

function normalizeModel(object: THREE.Object3D) {
    const box = new THREE.Box3().setFromObject(object);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxSide = Math.max(size.x, size.y, size.z, 1);

    object.position.sub(center);
    object.scale.setScalar(2.45 / maxSide);
    object.rotation.set(
        THREE.MathUtils.degToRad(-16),
        THREE.MathUtils.degToRad(30),
        THREE.MathUtils.degToRad(-6),
    );
}

function createFallbackModel() {
    const group = new THREE.Group();

    const body = new THREE.Mesh(
        new THREE.BoxGeometry(1.8, 1.35, 0.58, 4, 4, 2),
        modelMaterial,
    );
    body.castShadow = true;
    body.receiveShadow = true;
    group.add(body);

    const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.34, 0.08, 24, 72),
        modelMaterial,
    );
    ring.position.z = 0.32;
    group.add(ring);

    const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(body.geometry, 18),
        edgeMaterial,
    );
    body.add(edges);

    group.rotation.set(
        THREE.MathUtils.degToRad(-18),
        THREE.MathUtils.degToRad(34),
        THREE.MathUtils.degToRad(-8),
    );

    return group;
}

function fitCameraToObject(
    camera: THREE.PerspectiveCamera,
    controls: OrbitControls,
    object: THREE.Object3D,
) {
    const box = new THREE.Box3().setFromObject(object);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxSide = Math.max(size.x, size.y, size.z, 1);
    const distance = maxSide * 2.65;

    camera.position.set(distance, distance * 0.64, distance * 1.05);
    camera.near = distance / 100;
    camera.far = distance * 100;
    camera.updateProjectionMatrix();

    controls.target.copy(center);
    controls.minDistance = distance * 0.35;
    controls.maxDistance = distance * 5;
    controls.update();

    return {
        cameraPosition: camera.position.clone(),
        target: center.clone(),
    };
}

export function MockModelViewer({
    fileName,
    modelUrl,
    mode = "card",
    onExpand,
}: MockModelViewerProps) {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const sceneRef = useRef<ViewerScene | null>(null);
    const isModal = mode === "modal";

    useEffect(() => {
        const container = containerRef.current;

        if (!container) {
            return;
        }

        const scene = new THREE.Scene();
        scene.background = null;

        const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
        });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(renderer.domElement);

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.08;
        controls.enablePan = false;
        controls.rotateSpeed = 0.78;
        controls.zoomSpeed = 0.9;

        const ambientLight = new THREE.AmbientLight(0xffffff, 1.8);
        const keyLight = new THREE.DirectionalLight(0xffffff, 3.1);
        keyLight.position.set(4, 6, 5);
        keyLight.castShadow = true;

        const fillLight = new THREE.DirectionalLight(0xe9f0ff, 1.4);
        fillLight.position.set(-5, 2, 4);

        const rimLight = new THREE.DirectionalLight(0xffffff, 1.25);
        rimLight.position.set(-2, 4, -5);

        const grid = new THREE.GridHelper(5.6, 18, 0xdedede, 0xe9e9e9);
        grid.position.y = -1.18;
        grid.material.transparent = true;
        grid.material.opacity = 0.55;

        const shadowPlane = new THREE.Mesh(
            new THREE.PlaneGeometry(5.2, 5.2),
            new THREE.ShadowMaterial({ color: 0x000000, opacity: 0.1 }),
        );
        shadowPlane.rotation.x = -Math.PI / 2;
        shadowPlane.position.y = -1.2;
        shadowPlane.receiveShadow = true;

        scene.add(ambientLight, keyLight, fillLight, rimLight, grid, shadowPlane);

        function resize() {
            const { width, height } = container.getBoundingClientRect();
            const safeWidth = Math.max(width, 1);
            const safeHeight = Math.max(height, 1);

            renderer.setSize(safeWidth, safeHeight, false);
            camera.aspect = safeWidth / safeHeight;
            camera.updateProjectionMatrix();
        }

        const resizeObserver = new ResizeObserver(resize);
        resizeObserver.observe(container);
        resize();

        let frameId = 0;

        function animate() {
            controls.update();
            renderer.render(scene, camera);
            frameId = window.requestAnimationFrame(animate);
        }

        let isDisposed = false;

        const addObject = (object: THREE.Object3D) => {
            if (isDisposed) {
                disposeObject(object);
                return;
            }

            decorateModel(object);
            normalizeModel(object);
            scene.add(object);

            const { cameraPosition, target } = fitCameraToObject(
                camera,
                controls,
                object,
            );

            sceneRef.current = {
                camera,
                controls,
                renderer,
                initialCameraPosition: cameraPosition,
                initialTarget: target,
                object,
            };
        };

        if (modelUrl && fileName.toLowerCase().endsWith(".obj")) {
            const loader = new OBJLoader();
            loader.load(
                modelUrl,
                addObject,
                undefined,
                () => addObject(createFallbackModel()),
            );
        } else {
            addObject(createFallbackModel());
        }

        animate();

        return () => {
            isDisposed = true;
            window.cancelAnimationFrame(frameId);
            resizeObserver.disconnect();
            controls.dispose();
            renderer.dispose();
            renderer.domElement.remove();

            if (sceneRef.current?.object) {
                disposeObject(sceneRef.current.object);
            }

            sceneRef.current = null;
        };
    }, [fileName, modelUrl]);

    function zoom(multiplier: number) {
        const viewer = sceneRef.current;

        if (!viewer) {
            return;
        }

        const direction = viewer.camera.position
            .clone()
            .sub(viewer.controls.target)
            .multiplyScalar(multiplier);

        viewer.camera.position.copy(viewer.controls.target).add(direction);
        viewer.controls.update();
    }

    function resetView() {
        const viewer = sceneRef.current;

        if (!viewer) {
            return;
        }

        viewer.camera.position.copy(viewer.initialCameraPosition);
        viewer.controls.target.copy(viewer.initialTarget);
        viewer.controls.update();
    }

    return (
        <div className={isModal ? styles.viewerModal : styles.viewerCard}>
            <div className={styles.viewport}>
                <div ref={containerRef} className={styles.threeCanvas} />

                {!isModal && onExpand ? (
                    <button
                        type="button"
                        className={styles.expandButton}
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
                    onClick={() => zoom(0.84)}
                >
                    +
                </button>
                <button
                    type="button"
                    className={styles.controlButton}
                    onClick={() => zoom(1.16)}
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
