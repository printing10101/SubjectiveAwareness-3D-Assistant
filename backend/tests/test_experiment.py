from app.services.experiment import run_experiment


class TestRunExperiment:
    async def test_simple_experiment(self):
        result = await run_experiment("test_experiment", {"param1": "value1"})
        assert result["experiment_name"] == "test_experiment"
        assert result["status"] == "completed"
        assert result["params"] == {"param1": "value1"}
        assert "accuracy" in result["metrics"]
        assert "response_time" in result["metrics"]

    async def test_empty_params(self):
        result = await run_experiment("empty_test", {})
        assert result["experiment_name"] == "empty_test"
        assert result["params"] == {}

    async def test_complex_params(self):
        params = {"model": "deepseek-r1:7b", "temperature": 0.3, "top_k": 3}
        result = await run_experiment("sentencing_v2", params)
        assert result["params"] == params
