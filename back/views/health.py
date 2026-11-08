from back.core.views import View


class HealthView(View):
    paths = ("/health",)

    async def get(self) -> dict[str, str]:
        return {"status": "ok"}
