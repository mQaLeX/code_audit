#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="code-audit-agent"
IMAGE_TAG="latest"

build_image() {
    echo "========================================="
    echo "Building Code Audit Agent Docker Image"
    echo "========================================="
    echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""
    
    docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" "${SCRIPT_DIR}"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "========================================="
        echo "Build Successful!"
        echo "========================================="
        echo ""
        echo "To use this image:"
        echo "  python main.py c civetweb /path/to/code --docker-image ${IMAGE_NAME}:${IMAGE_TAG}"
        echo ""
        echo "To run a container manually:"
        echo "  docker run -it --rm -v /path/to/code:/workspace ${IMAGE_NAME}:${IMAGE_TAG}"
        echo ""
    else
        echo ""
        echo "========================================="
        echo "Build Failed!"
        echo "========================================="
        exit 1
    fi
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -t, --tag TAG       Specify image tag (default: latest)"
    echo "  -n, --name NAME     Specify image name (default: code-audit-agent)"
    echo ""
    echo "Examples:"
    echo "  $0                              # Build with default name and tag"
    echo "  $0 -t v1.0                      # Build with tag v1.0"
    echo "  $0 -n my-audit -t latest        # Build with custom name"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

build_image
