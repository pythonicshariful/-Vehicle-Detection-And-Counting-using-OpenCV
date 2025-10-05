import cv2
import numpy as np
import argparse


def center_handle(x, y, w, h):
    x1 = int(w / 2)
    y1 = int(h / 2)
    cx = x + x1
    cy = y + y1
    return cx, cy


def main(video_path=None, use_camera=False, device=0, count_line_position=None,
         min_width_react=80, min_hieght_react=80):
    if use_camera:
        cap = cv2.VideoCapture(device)
    else:
        cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise SystemExit('Cannot open video')

    # Create background subtractor, prefer bgsegm if available
    if hasattr(cv2, 'bgsegm'):
        try:
            fgbg = cv2.bgsegm.createBackgroundSubtractorMOG()
        except Exception:
            fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
    else:
        fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=True)

    up_count = 0
    down_count = 0
    # total count will be up_count + down_count
    min_contour_area = 500
    next_object_id = 0
    objects = {}  # obj_id -> {'y': int, 'counted': bool, 'missed': int, 'prev_y': int}

    # read first frame (to get frame size and default line position)
    ret, frame = cap.read()
    if not ret:
        raise SystemExit('Cannot read first frame')
    h, w = frame.shape[:2]
    if count_line_position is None:
        line_position = int(h * 2 / 3)
    else:
        line_position = count_line_position
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        fgmask = fgbg.apply(frame)
        _, fgmask = cv2.threshold(fgmask, 250, 255, cv2.THRESH_BINARY)
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_DILATE, np.ones((5, 5), np.uint8))

        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        current_centroids = []
        for contour in contours:
                if cv2.contourArea(contour) > min_contour_area:
                    x, y, w_box, h_box = cv2.boundingRect(contour)
                    # filter by min width/height
                    # if w_box < min_width_react or h_box < min_hieght_react:
                    #     continue
                    cx, cy = center_handle(x, y, w_box, h_box)
                    current_centroids.append({'cx': cx, 'cy': cy, 'x': x, 'y': y, 'w': w_box, 'h': h_box})
        used_ids = set()
        for c in current_centroids:
            cx = c['cx']
            cy = c['cy']
            x = c['x']
            y = c['y']
            w_box = c['w']
            h_box = c['h']

            matched_id = None
            min_dist = 1e9
            for obj_id, info in objects.items():
                dist = abs(info['y'] - cy)
                if dist < 60 and dist < min_dist:
                    min_dist = dist
                    matched_id = obj_id

            if matched_id is None:
                matched_id = next_object_id
                objects[matched_id] = {'y': cy, 'counted': False, 'missed': 0, 'prev_y': None}
                next_object_id += 1
            else:
                objects[matched_id]['y'] = cy
                objects[matched_id]['missed'] = 0

            used_ids.add(matched_id)

            # change box color if counted
            box_color = (0, 255, 0)
            if objects[matched_id].get('counted'):
                # green for down, blue for up, magenta default
                direction = objects[matched_id].get('direction')
                if direction == 'down':
                    box_color = (0, 128, 255)  # orange-ish
                elif direction == 'up':
                    box_color = (255, 0, 0)  # blue
                else:
                    box_color = (255, 0, 255)

            cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), box_color, 2)
            cv2.circle(frame, (cx, cy), 3, (0, 0, 255), -1)
            cv2.putText(frame, str(matched_id), (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

            # detect crossing direction: top->bottom is 'down', bottom->top is 'up'
            if not objects[matched_id]['counted']:
                prev_y = objects[matched_id].get('prev_y')
                if prev_y is not None:
                    # crossed downwards
                    if prev_y < line_position and cy >= line_position:
                        down_count += 1
                        objects[matched_id]['counted'] = True
                        objects[matched_id]['direction'] = 'down'
                    # crossed upwards
                    elif prev_y > line_position and cy <= line_position:
                        up_count += 1
                        objects[matched_id]['counted'] = True
                        objects[matched_id]['direction'] = 'up'
                objects[matched_id]['prev_y'] = cy

        remove_ids = []
        for obj_id, info in list(objects.items()):
            if obj_id not in used_ids:
                info['missed'] += 1
                if info['missed'] > 10:
                    remove_ids.append(obj_id)
        for rid in remove_ids:
            objects.pop(rid, None)

        # draw counting line and counts (up, down, total)
        total = up_count + down_count
        cv2.line(frame, (0, line_position), (w, line_position), (255, 0, 255), 2)
        cv2.putText(frame, f'Up: {up_count}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        cv2.putText(frame, f'Down: {down_count}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, f'Total: {total}', (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow('Frame', frame)
        cv2.imshow('FG Mask', fgmask)

        if cv2.waitKey(30) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Vehicle counter')
    parser.add_argument('--video', '-v', default='video.mp4', help='Path to video file')
    parser.add_argument('--camera', action='store_true', help='Use webcam instead of video file')
    parser.add_argument('--device', type=int, default=0, help='Camera device id (when using --camera)')
    parser.add_argument('--count-line-position', type=int, default=None, help='Y position of the counting line (px)')
    # accept the misspelled alias the user used
    parser.add_argument('--count_line_postion', type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument('--min-width-react', type=int, default=80, help='Minimum bounding box width to consider')
    parser.add_argument('--min-height-react', type=int, default=80, help='Minimum bounding box height to consider')

    args = parser.parse_args()
    # prefer the alias if provided (backwards compatibility)
    count_line_pos = args.count_line_postion if args.count_line_postion is not None else args.count_line_position

    main(video_path=args.video,
         use_camera=args.camera,
         device=args.device,
         count_line_position=count_line_pos,
         min_width_react=args.min_width_react,
         min_hieght_react=args.min_height_react)


