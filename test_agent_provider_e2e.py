import os
import pytest

pytestmark = pytest.mark.integration


def test_real_provider_and_postgres_configuration_available():
    """Gate test: run explicitly in an integration environment, never with secrets in source."""
    required = ['DATABASE_URL', 'AI_API_KEY', 'AI_MODEL']
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip('Integration gate requires: ' + ', '.join(missing))
    assert os.getenv('DATABASE_URL').startswith(('postgresql://', 'postgresql+psycopg://'))
    assert os.getenv('AI_API_KEY')
    assert os.getenv('AI_MODEL')
