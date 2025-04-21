// === Data Models ===
open class Point3D(var x: Int, var y: Int, var z: Int)

class BallTrajectoryPoint(x: Int, y: Int, z: Int, var timeStamp: Double = 0.0) : Point3D(x, y, z)

class ImpactPoint(
    x: Int,
    y: Int,
    z: Int,
    var speed: Double = 0.0,
    var spinAxis: DoubleArray = doubleArrayOf(0.0, 0.0, 0.0),
    var surface: String? = null
) : Point3D(x, y, z)

class TrajectoryAnalysisResult {
    var label: String? = null        // OUT, NOT_OUT, LBW, CAUGHT, RUN_OUT, etc.
    var confidence: Double = 0.0
    var impactPoint: ImpactPoint? = null
    var predictedTrajectory: List<BallTrajectoryPoint>? = null
    var batCoordinates: List<Point3D>? = null
    var stumpCoordinates: List<Point3D>? = null
}

class VideoStreamConfig {
    var width: Int = 0
    var height: Int = 0
    var cameraId: String? = null
    // Add other config fields like frameRate, outputPath, encodingOptions
}

// === Overlay Module Interface ===
interface StreamOverlayModule {
    fun initialize(config: VideoStreamConfig)
    fun receiveTrajectoryData(data: TrajectoryAnalysisResult)
    fun finalizeVideo(outputPath: String)
}

// === Decision Module Interface ===
interface DecisionModule {
    // Analyzes the trajectory data and returns it with an updated label/confidence
    fun decide(data: TrajectoryAnalysisResult): TrajectoryAnalysisResult
}

// === LBW Decision Module ===
class LbwDecisionModule : DecisionModule {
    override fun decide(data: TrajectoryAnalysisResult): TrajectoryAnalysisResult {
        // TODO: Replace with actual LBW criteria (impact location, leg contact, stump line)
        val meetsLbwCriteria = (data.impactPoint != null && data.stumpCoordinates != null)
        if (meetsLbwCriteria) {
            data.label = "LBW"
            data.confidence = 0.95 // stub value
            return data
        }
        return data
    }
}

// === Caught Decision Module ===
class CaughtDecisionModule : DecisionModule {
    override fun decide(data: TrajectoryAnalysisResult): TrajectoryAnalysisResult {
        // TODO: Replace with real edge-detection logic
        val batHit = !data.batCoordinates.isNullOrEmpty()
        if (batHit) {
            data.label = "CAUGHT"
            data.confidence = 0.90
            return data
        }
        return data
    }
}

// === Run-Out Decision Module ===
class RunOutDecisionModule : DecisionModule {
    override fun decide(data: TrajectoryAnalysisResult): TrajectoryAnalysisResult {
        // TODO: Add actual run-out detection logic based on stump proximity and timing
        val closeToStumps = !data.stumpCoordinates.isNullOrEmpty()
        if (closeToStumps && data.label == null) {
            data.label = "RUN_OUT"
            data.confidence = 0.85
            return data
        }
        return data
    }
}

// === Decision Maker to Chain Modules ===
class DecisionMaker(private val modules: List<DecisionModule>) {
    fun makeDecision(data: TrajectoryAnalysisResult): TrajectoryAnalysisResult {
        for (module in modules) {
            val result = module.decide(data)
            if (result.label != null) return result
        }
        // Default to NOT_OUT if no module claimed it
        data.label = "NOT_OUT"
        data.confidence = 1.0
        return data
    }
}

// === Stream Analysis & Overlay Implementation ===
class StreamAnalysis : StreamOverlayModule {
    private lateinit var config: VideoStreamConfig
    private val decisionMaker = DecisionMaker(
        listOf(
            LbwDecisionModule(),
            CaughtDecisionModule(),
            RunOutDecisionModule()
        )
    )

    override fun initialize(config: VideoStreamConfig) {
        this.config = config
        // TODO: Load calibration, initialize JavaCV/JavaFX contexts, preload assets
    }

    override fun receiveTrajectoryData(data: TrajectoryAnalysisResult) {
        // Separate decision logic
        val decidedData = decisionMaker.makeDecision(data)

        // TODO: Pass decidedData to overlay rendering pipeline
        println("Decision: ${decidedData.label} with confidence ${decidedData.confidence}")
    }

    override fun finalizeVideo(outputPath: String) {
        // TODO: Use JCodec or JAVE to save the composed video to outputPath
    }
}
