from django.core.management.base import BaseCommand, CommandError

from training.retention import cleanup_expired_sessions


class Command(BaseCommand):
    help = "30분 이상 방치된 훈련 세션의 대화 원문을 파기합니다."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        if batch_size < 1:
            raise CommandError("--batch-size는 1 이상이어야 합니다.")

        total = 0
        while True:
            count = cleanup_expired_sessions(batch_size=batch_size)
            total += count
            if count < batch_size:
                break

        self.stdout.write(self.style.SUCCESS(f"만료 세션 {total}개의 원문을 파기했습니다."))
