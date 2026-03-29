/* ═══════════════════════════════════════════════════════════════════════════
   3D EARTH GLOBE WITH THREE.JS
   Interactive Earth visualization with aurora zones and satellite tracking
   ═══════════════════════════════════════════════════════════════════════════ */

class EarthGlobe {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;
        
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.earth = null;
        this.clouds = null;
        this.atmosphere = null;
        this.auroraRings = [];
        this.satellites = [];
        this.currentView = 'aurora';
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.tooltip = null;
        
        this.init();
        this.animate();
        this.setupControls();
        this.setupTooltip();
    }
    
    init() {
        // Scene setup
        this.scene = new THREE.Scene();
        
        // Camera setup
        this.camera = new THREE.PerspectiveCamera(
            45,
            this.container.clientWidth / this.container.clientHeight,
            0.1,
            1000
        );
        this.camera.position.z = 3;
        
        // Renderer setup
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true, 
            alpha: true 
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);
        
        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(5, 3, 5);
        this.scene.add(directionalLight);
        
        // Create Earth
        this.createEarth();
        this.createClouds();
        this.createAtmosphere();
        this.createAuroraZones();
        this.createSatellites();
        
        // Stars background
        this.createStars();
        
        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());
        
        // Mouse move for tooltip
        this.renderer.domElement.addEventListener('mousemove', (event) => this.onMouseMove(event));
    }
    
    createEarth() {
        const geometry = new THREE.SphereGeometry(1, 64, 64);
        
        // Load Earth texture
        const textureLoader = new THREE.TextureLoader();
        
        // Using NASA's Blue Marble texture
        const earthTexture = textureLoader.load(
            'https://unpkg.com/three-globe@2.31.0/example/img/earth-blue-marble.jpg',
            () => {
                console.log('Earth texture loaded successfully');
            },
            undefined,
            (error) => {
                console.error('Error loading Earth texture:', error);
            }
        );
        
        // Optional: Load bump map for terrain detail
        const bumpMap = textureLoader.load(
            'https://unpkg.com/three-globe@2.31.0/example/img/earth-topology.png'
        );
        
        const material = new THREE.MeshPhongMaterial({
            map: earthTexture,
            bumpMap: bumpMap,
            bumpScale: 0.05,
            specular: 0x333333,
            shininess: 15
        });
        
        this.earth = new THREE.Mesh(geometry, material);
        this.scene.add(this.earth);
    }
    
    createClouds() {
        const geometry = new THREE.SphereGeometry(1.01, 64, 64);
        const material = new THREE.MeshPhongMaterial({
            color: 0xffffff,
            transparent: true,
            opacity: 0.2
        });
        
        this.clouds = new THREE.Mesh(geometry, material);
        this.scene.add(this.clouds);
    }
    
    createAtmosphere() {
        const geometry = new THREE.SphereGeometry(1.1, 64, 64);
        const material = new THREE.MeshBasicMaterial({
            color: 0x00d9ff,
            transparent: true,
            opacity: 0.1,
            side: THREE.BackSide
        });
        
        this.atmosphere = new THREE.Mesh(geometry, material);
        this.scene.add(this.atmosphere);
    }
    
    createAuroraZones() {
        // Northern aurora zone
        const northGeometry = new THREE.TorusGeometry(0.4, 0.05, 16, 100);
        const northMaterial = new THREE.MeshBasicMaterial({
            color: 0x00ff88,
            transparent: true,
            opacity: 0.6
        });
        const northAurora = new THREE.Mesh(northGeometry, northMaterial);
        northAurora.rotation.x = Math.PI / 2;
        northAurora.position.y = 0.8;
        this.auroraRings.push(northAurora);
        this.scene.add(northAurora);
        
        // Southern aurora zone
        const southGeometry = new THREE.TorusGeometry(0.4, 0.05, 16, 100);
        const southMaterial = new THREE.MeshBasicMaterial({
            color: 0x00ff88,
            transparent: true,
            opacity: 0.6
        });
        const southAurora = new THREE.Mesh(southGeometry, southMaterial);
        southAurora.rotation.x = Math.PI / 2;
        southAurora.position.y = -0.8;
        this.auroraRings.push(southAurora);
        this.scene.add(southAurora);
    }
    
    createSatellites() {
        // Daha dağınık ve rastgele pozisyonlar - 18 uydu
        const satellitePositions = [
            // Uluslararası Uydular (9 adet)
            { x: 1.6, y: 0.3, z: 0.4, name: 'DSCOVR' },
            { x: -1.5, y: -0.5, z: 0.6, name: 'ACE' },
            { x: 0.7, y: 1.7, z: -0.3, name: 'GOES-16' },
            { x: -0.4, y: -1.6, z: 0.8, name: 'SDO' },
            { x: 1.3, y: 0.9, z: -0.7, name: 'TÜRKSAT 5A' },
            { x: 1.4, y: -0.8, z: 0.9, name: 'FENGYUN-3E' },
            { x: -1.2, y: 1.1, z: -0.5, name: 'KUAFU-1' },
            { x: 0.9, y: -1.3, z: -0.8, name: 'ELECTRO-L N3' },
            { x: -1.6, y: 0.6, z: 0.2, name: 'HIMAWARI-9' },
            
            // Türk Uyduları (9 adet)
            { x: 1.1, y: 1.4, z: 0.5, name: 'TÜRKSAT-5A' },
            { x: -0.8, y: 1.5, z: -0.6, name: 'TÜRKSAT-5B' },
            { x: 1.5, y: -0.3, z: -0.9, name: 'TÜRKSAT-4A' },
            { x: -1.4, y: -0.9, z: 0.7, name: 'TÜRKSAT-4B' },
            { x: 0.5, y: 1.2, z: 1.3, name: 'TÜRKSAT-3A' },
            { x: -0.6, y: -0.4, z: 1.7, name: 'İMECE' },
            { x: 0.3, y: 0.8, z: -1.6, name: 'RASAT' },
            { x: -1.1, y: -1.2, z: -0.4, name: 'GÖKTÜRK-1' },
            { x: 1.7, y: 0.5, z: 0.1, name: 'GÖKTÜRK-2' }
        ];
        
        satellitePositions.forEach(pos => {
            // Create ultra-detailed satellite group
            const satelliteGroup = new THREE.Group();
            
            // Uydu boyutunu küçültmek için scale faktörü
            const scale = 0.5; // Tüm boyutları yarıya indir
            
            // Main body - high poly rounded box with segments
            const bodyGeometry = new THREE.BoxGeometry(0.08 * scale, 0.05 * scale, 0.05 * scale, 8, 8, 8);
            const bodyMaterial = new THREE.MeshStandardMaterial({
                color: 0xd4d4d4,
                metalness: 0.9,
                roughness: 0.1,
                emissive: 0x111111
            });
            const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
            satelliteGroup.add(body);
            
            // Equipment boxes on body
            const boxGeometry = new THREE.BoxGeometry(0.02 * scale, 0.015 * scale, 0.015 * scale, 2, 2, 2);
            const boxMaterial = new THREE.MeshStandardMaterial({
                color: 0x444444,
                metalness: 0.8,
                roughness: 0.2
            });
            
            // Add multiple equipment boxes
            for (let i = 0; i < 6; i++) {
                const box = new THREE.Mesh(boxGeometry, boxMaterial);
                const angle = (i / 6) * Math.PI * 2;
                box.position.set(
                    Math.cos(angle) * 0.042 * scale,
                    (i % 2 === 0 ? 0.01 : -0.01) * scale,
                    Math.sin(angle) * 0.042 * scale
                );
                satelliteGroup.add(box);
            }
            
            // Detail panels with rivets
            const detailGeometry = new THREE.BoxGeometry(0.081 * scale, 0.015 * scale, 0.051 * scale);
            const detailMaterial = new THREE.MeshStandardMaterial({
                color: 0x333333,
                metalness: 0.7,
                roughness: 0.3
            });
            const detail1 = new THREE.Mesh(detailGeometry, detailMaterial);
            detail1.position.y = 0.015 * scale;
            satelliteGroup.add(detail1);
            
            const detail2 = new THREE.Mesh(detailGeometry, detailMaterial);
            detail2.position.y = -0.015 * scale;
            satelliteGroup.add(detail2);
            
            // Add rivets to panels
            const rivetGeometry = new THREE.CylinderGeometry(0.001 * scale, 0.001 * scale, 0.002 * scale, 8);
            const rivetMaterial = new THREE.MeshStandardMaterial({
                color: 0x666666,
                metalness: 0.9,
                roughness: 0.1
            });
            
            for (let x = -0.03 * scale; x <= 0.03 * scale; x += 0.015 * scale) {
                for (let z = -0.02 * scale; z <= 0.02 * scale; z += 0.02 * scale) {
                    const rivet = new THREE.Mesh(rivetGeometry, rivetMaterial);
                    rivet.position.set(x, 0.015 * scale, z);
                    rivet.rotation.x = Math.PI / 2;
                    satelliteGroup.add(rivet);
                }
            }
            
            // Solar panels - ultra high quality with detailed grid
            const panelGeometry = new THREE.BoxGeometry(0.12 * scale, 0.06 * scale, 0.005 * scale, 12, 12, 1);
            const panelMaterial = new THREE.MeshStandardMaterial({
                color: 0x1a4d7a,
                emissive: 0x0a1d3c,
                metalness: 0.6,
                roughness: 0.4
            });
            
            // Left panel with connection arm
            const leftPanel = new THREE.Mesh(panelGeometry, panelMaterial);
            leftPanel.position.set(-0.1 * scale, 0, 0);
            satelliteGroup.add(leftPanel);
            
            // Panel connection arm (left)
            const armGeometry = new THREE.CylinderGeometry(0.003 * scale, 0.003 * scale, 0.02 * scale, 16);
            const armMaterial = new THREE.MeshStandardMaterial({
                color: 0x999999,
                metalness: 0.9,
                roughness: 0.1
            });
            const leftArm = new THREE.Mesh(armGeometry, armMaterial);
            leftArm.position.set(-0.05 * scale, 0, 0);
            leftArm.rotation.z = Math.PI / 2;
            satelliteGroup.add(leftArm);
            
            // Left panel frame with detail
            const frameGeometry = new THREE.BoxGeometry(0.122 * scale, 0.062 * scale, 0.003 * scale);
            const frameMaterial = new THREE.MeshStandardMaterial({
                color: 0x888888,
                metalness: 0.8,
                roughness: 0.2
            });
            const leftFrame = new THREE.Mesh(frameGeometry, frameMaterial);
            leftFrame.position.set(-0.1 * scale, 0, -0.004 * scale);
            satelliteGroup.add(leftFrame);
            
            // Add solar cell grid lines on left panel
            const lineGeometry = new THREE.BoxGeometry(0.12 * scale, 0.001 * scale, 0.006 * scale);
            const lineMaterial = new THREE.MeshStandardMaterial({
                color: 0x333333,
                metalness: 0.5,
                roughness: 0.5
            });
            for (let i = -0.025 * scale; i <= 0.025 * scale; i += 0.01 * scale) {
                const line = new THREE.Mesh(lineGeometry, lineMaterial);
                line.position.set(-0.1 * scale, i, 0.001 * scale);
                satelliteGroup.add(line);
            }
            
            // Right panel with connection arm
            const rightPanel = new THREE.Mesh(panelGeometry, panelMaterial);
            rightPanel.position.set(0.1 * scale, 0, 0);
            satelliteGroup.add(rightPanel);
            
            // Panel connection arm (right)
            const rightArm = new THREE.Mesh(armGeometry, armMaterial);
            rightArm.position.set(0.05 * scale, 0, 0);
            rightArm.rotation.z = Math.PI / 2;
            satelliteGroup.add(rightArm);
            
            // Right panel frame
            const rightFrame = new THREE.Mesh(frameGeometry, frameMaterial);
            rightFrame.position.set(0.1 * scale, 0, -0.004 * scale);
            satelliteGroup.add(rightFrame);
            
            // Add solar cell grid lines on right panel
            for (let i = -0.025 * scale; i <= 0.025 * scale; i += 0.01 * scale) {
                const line = new THREE.Mesh(lineGeometry, lineMaterial);
                line.position.set(0.1 * scale, i, 0.001 * scale);
                satelliteGroup.add(line);
            }
            
            // Main antenna mast - segmented
            const mastGeometry = new THREE.CylinderGeometry(0.006 * scale, 0.008 * scale, 0.04 * scale, 32);
            const mastMaterial = new THREE.MeshStandardMaterial({
                color: 0xffd700,
                metalness: 0.9,
                roughness: 0.1,
                emissive: 0x332200
            });
            const mast = new THREE.Mesh(mastGeometry, mastMaterial);
            mast.position.set(0, 0.045 * scale, 0);
            satelliteGroup.add(mast);
            
            // Antenna segments (rings)
            for (let i = 0; i < 3; i++) {
                const ringGeometry = new THREE.TorusGeometry(0.008 * scale, 0.001 * scale, 16, 32);
                const ringMaterial = new THREE.MeshStandardMaterial({
                    color: 0xcccccc,
                    metalness: 0.9,
                    roughness: 0.1
                });
                const ring = new THREE.Mesh(ringGeometry, ringMaterial);
                ring.position.set(0, (0.03 + (i * 0.015)) * scale, 0);
                ring.rotation.x = Math.PI / 2;
                satelliteGroup.add(ring);
            }
            
            // Main dish antenna - ultra detailed
            const dishGeometry = new THREE.CylinderGeometry(0.025 * scale, 0.02 * scale, 0.015 * scale, 64);
            const dishMaterial = new THREE.MeshStandardMaterial({
                color: 0xf0f0f0,
                metalness: 0.8,
                roughness: 0.2,
                side: THREE.DoubleSide
            });
            const dish = new THREE.Mesh(dishGeometry, dishMaterial);
            dish.position.set(0, 0.07 * scale, 0);
            satelliteGroup.add(dish);
            
            // Dish inner surface with detail
            const dishInnerGeometry = new THREE.CircleGeometry(0.022 * scale, 64);
            const dishInnerMaterial = new THREE.MeshStandardMaterial({
                color: 0xcccccc,
                metalness: 0.9,
                roughness: 0.1
            });
            const dishInner = new THREE.Mesh(dishInnerGeometry, dishInnerMaterial);
            dishInner.position.set(0, 0.0775 * scale, 0);
            dishInner.rotation.x = -Math.PI / 2;
            satelliteGroup.add(dishInner);
            
            // Dish support struts
            for (let i = 0; i < 4; i++) {
                const strutGeometry = new THREE.CylinderGeometry(0.001 * scale, 0.001 * scale, 0.02 * scale, 8);
                const strutMaterial = new THREE.MeshStandardMaterial({
                    color: 0xaaaaaa,
                    metalness: 0.9,
                    roughness: 0.1
                });
                const strut = new THREE.Mesh(strutGeometry, strutMaterial);
                const angle = (i / 4) * Math.PI * 2;
                strut.position.set(
                    Math.cos(angle) * 0.015 * scale,
                    0.0675 * scale,
                    Math.sin(angle) * 0.015 * scale
                );
                strut.rotation.x = Math.PI / 4;
                strut.rotation.y = angle;
                satelliteGroup.add(strut);
            }
            
            // Feed horn at center of dish
            const hornGeometry = new THREE.ConeGeometry(0.004 * scale, 0.01 * scale, 16);
            const hornMaterial = new THREE.MeshStandardMaterial({
                color: 0xffd700,
                metalness: 0.9,
                roughness: 0.1
            });
            const horn = new THREE.Mesh(hornGeometry, hornMaterial);
            horn.position.set(0, 0.073 * scale, 0);
            horn.rotation.x = Math.PI;
            satelliteGroup.add(horn);
            
            // Communication antennas (detailed rods with tips)
            for (let i = 0; i < 4; i++) {
                const rodGeometry = new THREE.CylinderGeometry(0.002 * scale, 0.002 * scale, 0.03 * scale, 16);
                const rodMaterial = new THREE.MeshStandardMaterial({
                    color: 0xaaaaaa,
                    metalness: 0.9,
                    roughness: 0.1
                });
                const rod = new THREE.Mesh(rodGeometry, rodMaterial);
                const angle = (i / 4) * Math.PI * 2;
                rod.position.set(
                    Math.cos(angle) * 0.03 * scale,
                    0.02 * scale,
                    Math.sin(angle) * 0.03 * scale
                );
                rod.rotation.z = angle;
                satelliteGroup.add(rod);
                
                // Antenna tips
                const tipGeometry = new THREE.SphereGeometry(0.003 * scale, 16, 16);
                const tipMaterial = new THREE.MeshStandardMaterial({
                    color: 0xff6600,
                    emissive: 0xff3300,
                    emissiveIntensity: 1.5
                });
                const tip = new THREE.Mesh(tipGeometry, tipMaterial);
                tip.position.set(
                    Math.cos(angle) * 0.045 * scale,
                    0.02 * scale,
                    Math.sin(angle) * 0.045 * scale
                );
                satelliteGroup.add(tip);
            }
            
            // Sensors and cameras
            const sensorGeometry = new THREE.CylinderGeometry(0.004 * scale, 0.004 * scale, 0.008 * scale, 16);
            const sensorMaterial = new THREE.MeshStandardMaterial({
                color: 0x222222,
                metalness: 0.7,
                roughness: 0.3
            });
            
            // Front sensor
            const frontSensor = new THREE.Mesh(sensorGeometry, sensorMaterial);
            frontSensor.position.set(0, 0, 0.03 * scale);
            frontSensor.rotation.x = Math.PI / 2;
            satelliteGroup.add(frontSensor);
            
            // Sensor lens
            const lensGeometry = new THREE.CircleGeometry(0.003 * scale, 16);
            const lensMaterial = new THREE.MeshStandardMaterial({
                color: 0x0066ff,
                emissive: 0x0033ff,
                emissiveIntensity: 1,
                metalness: 0.9,
                roughness: 0.1
            });
            const lens = new THREE.Mesh(lensGeometry, lensMaterial);
            lens.position.set(0, 0, 0.034 * scale);
            satelliteGroup.add(lens);
            
            // Status LEDs (multiple colors)
            const ledPositions = [
                { x: 0.035 * scale, y: 0, z: 0.026 * scale, color: 0x00ff00 },
                { x: -0.035 * scale, y: 0, z: 0.026 * scale, color: 0x00ff00 },
                { x: 0, y: 0.022 * scale, z: 0.026 * scale, color: 0xff0000 },
                { x: 0, y: -0.022 * scale, z: 0.026 * scale, color: 0xffff00 }
            ];
            
            ledPositions.forEach(led => {
                const lightGeometry = new THREE.SphereGeometry(0.003 * scale, 16, 16);
                const lightMaterial = new THREE.MeshStandardMaterial({
                    color: led.color,
                    emissive: led.color,
                    emissiveIntensity: 2
                });
                const light = new THREE.Mesh(lightGeometry, lightMaterial);
                light.position.set(led.x, led.y, led.z);
                satelliteGroup.add(light);
            });
            
            // Thermal radiators (side panels)
            const radiatorGeometry = new THREE.BoxGeometry(0.015 * scale, 0.04 * scale, 0.002 * scale);
            const radiatorMaterial = new THREE.MeshStandardMaterial({
                color: 0x666666,
                metalness: 0.6,
                roughness: 0.4
            });
            
            const leftRadiator = new THREE.Mesh(radiatorGeometry, radiatorMaterial);
            leftRadiator.position.set(-0.042 * scale, 0, 0);
            satelliteGroup.add(leftRadiator);
            
            const rightRadiator = new THREE.Mesh(radiatorGeometry, radiatorMaterial);
            rightRadiator.position.set(0.042 * scale, 0, 0);
            satelliteGroup.add(rightRadiator);
            
            // Cables/wires connecting panels
            const cableGeometry = new THREE.CylinderGeometry(0.0008 * scale, 0.0008 * scale, 0.04 * scale, 8);
            const cableMaterial = new THREE.MeshStandardMaterial({
                color: 0x333333,
                metalness: 0.5,
                roughness: 0.5
            });
            
            for (let i = 0; i < 2; i++) {
                const cable = new THREE.Mesh(cableGeometry, cableMaterial);
                cable.position.set(-0.05 * scale, (i === 0 ? 0.015 : -0.015) * scale, 0);
                cable.rotation.z = Math.PI / 2;
                satelliteGroup.add(cable);
                
                const cable2 = new THREE.Mesh(cableGeometry, cableMaterial);
                cable2.position.set(0.05 * scale, (i === 0 ? 0.015 : -0.015) * scale, 0);
                cable2.rotation.z = Math.PI / 2;
                satelliteGroup.add(cable2);
            }
            
            // Position the satellite group
            satelliteGroup.position.set(pos.x, pos.y, pos.z);
            satelliteGroup.userData.name = pos.name;
            
            // Basit orbit parametreleri
            satelliteGroup.userData.orbitIndex = this.satellites.length; // Uydu sırası
            
            // Add subtle rotation for realism
            satelliteGroup.rotation.x = Math.random() * 0.3;
            satelliteGroup.rotation.z = Math.random() * 0.3;
            
            // Add to satellites array and scene
            this.satellites.push(satelliteGroup);
            this.scene.add(satelliteGroup);
        });
    }
    
    createStars() {
        const starsGeometry = new THREE.BufferGeometry();
        const starsMaterial = new THREE.PointsMaterial({
            color: 0xffffff,
            size: 0.02
        });
        
        const starsVertices = [];
        for (let i = 0; i < 1000; i++) {
            const x = (Math.random() - 0.5) * 20;
            const y = (Math.random() - 0.5) * 20;
            const z = (Math.random() - 0.5) * 20;
            starsVertices.push(x, y, z);
        }
        
        starsGeometry.setAttribute('position', new THREE.Float32BufferAttribute(starsVertices, 3));
        const stars = new THREE.Points(starsGeometry, starsMaterial);
        this.scene.add(stars);
    }
    
    setupControls() {
        const buttons = document.querySelectorAll('.globe-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentView = btn.dataset.view;
                this.updateView();
            });
        });
    }
    
    setupTooltip() {
        // Create tooltip element
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'satellite-tooltip';
        document.body.appendChild(this.tooltip);
    }
    
    onMouseMove(event) {
        if (!this.renderer || !this.camera) return;
        
        // Calculate mouse position in normalized device coordinates
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        // Update raycaster
        this.raycaster.setFromCamera(this.mouse, this.camera);
        
        // Check for intersections with satellites
        const intersects = this.raycaster.intersectObjects(this.satellites, true);
        
        if (intersects.length > 0) {
            // Find the parent satellite group
            let satelliteGroup = intersects[0].object;
            while (satelliteGroup.parent && !satelliteGroup.userData.name) {
                satelliteGroup = satelliteGroup.parent;
            }
            
            if (satelliteGroup.userData.name) {
                // Show tooltip
                this.tooltip.textContent = satelliteGroup.userData.name;
                this.tooltip.style.left = event.clientX + 15 + 'px';
                this.tooltip.style.top = event.clientY + 15 + 'px';
                this.tooltip.classList.add('visible');
                this.renderer.domElement.style.cursor = 'pointer';
            }
        } else {
            // Hide tooltip
            this.tooltip.classList.remove('visible');
            this.renderer.domElement.style.cursor = 'default';
        }
    }
    
    updateView() {
        // Update visibility based on current view
        this.auroraRings.forEach(ring => {
            ring.visible = this.currentView === 'aurora';
        });
        
        this.satellites.forEach(sat => {
            sat.visible = this.currentView === 'satellites';
        });
    }
    
    updateAuroraIntensity(kpIndex) {
        const intensity = Math.min(kpIndex / 9, 1);
        this.auroraRings.forEach(ring => {
            ring.material.opacity = 0.3 + (intensity * 0.7);
            ring.scale.set(1 + intensity * 0.2, 1 + intensity * 0.2, 1);
        });
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        // Rotate Earth counter-clockwise (saat yönünün tersine)
        if (this.earth) {
            this.earth.rotation.y -= 0.001; // Negatif değer = saat yönünün tersi
        }
        
        // Rotate clouds slightly faster, also counter-clockwise
        if (this.clouds) {
            this.clouds.rotation.y -= 0.0012;
        }
        
        // Pulse aurora rings
        this.auroraRings.forEach((ring, index) => {
            const time = Date.now() * 0.001;
            ring.material.opacity = 0.4 + Math.sin(time + index) * 0.2;
        });
        
        // Orbit satellites - basit dairesel hareket
        this.satellites.forEach((sat, index) => {
            const time = Date.now() * 0.0005;
            const angle = time + (index * Math.PI * 2 / 18); // 18 uydu için eşit dağılım
            const radius = 1.5;
            sat.position.x = Math.cos(angle) * radius;
            sat.position.z = Math.sin(angle) * radius;
        });
        
        this.renderer.render(this.scene, this.camera);
    }
    
    onWindowResize() {
        if (!this.container) return;
        
        this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    }
    
    destroy() {
        // Cleanup tooltip
        if (this.tooltip && this.tooltip.parentNode) {
            this.tooltip.parentNode.removeChild(this.tooltip);
        }
    }
}

// Initialize globe when DOM is ready
let earthGlobe = null;
document.addEventListener('DOMContentLoaded', () => {
    if (typeof THREE !== 'undefined') {
        earthGlobe = new EarthGlobe('earth-globe');
    }
});