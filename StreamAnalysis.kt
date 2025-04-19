open class Point3D(var x: Int, var y: Int, var z: Int) {
}


class BallTrajectoryPoint(x: Int, y: Int, z: Int, var timeStamp: Double = 0.0) : Point3D(x, y, z) {
}


class ImpactPoint(x: Int, y: Int, z: Int, var speed: Double = 0.0, var spin_axis: DoubleArray, var surface: String? = null) : Point3D(x, y, z) {
}


class TrajectoryAnalysisResult {
    var label: String? = null // OUT or NOT OUT
    var confidence: Double = 0.0
    var impact_point: ImpactPoint? = null
    var predicted_trajectory: List<BallTrajectoryPoint>? = null
    var bat_coordinates: List<Point3D>? = null
    var stump_coordinates: List<Point3D>? = null
}


class VideoStreamConfig {
    var width: Int = 0
    var height: Int = 0
    var cameraId: String? = null
    // var calibration: CalibrationData? = null // Add frame rate, output path, encoding preferences
}


interface StreamOverlayModule {
    fun initialize(config: VideoStreamConfig?) // Camera config or source

    fun receiveTrajectoryData(data: TrajectoryAnalysisResult?)

    // fun renderOverlay(frame: Frame?) // Called for each frame with object tracking

    fun finalizeVideo(outputPath: String?) // Save or stream final video
}


class StreamAnalysis : StreamOverlayModule{
    override fun initialize(config: VideoStreamConfig?) {
        TODO("Not yet implemented")
    }

    override fun receiveTrajectoryData(data: TrajectoryAnalysisResult?) {
        TODO("Not yet implemented")
    }

    override fun finalizeVideo(outputPath: String?) {
        TODO("Not yet implemented")
    }
}